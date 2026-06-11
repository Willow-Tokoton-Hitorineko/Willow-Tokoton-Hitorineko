"""本地 HTTP 服务器 — 交互式城市采集界面 + SSE + 结果缓存。

用法:
    python -m ggf_agent.server          # 启动 localhost:8765
    python -m ggf_agent.server --port 9000
    浏览器打开 http://127.0.0.1:8765
"""
from __future__ import annotations

import json, sys, os, signal
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from urllib.parse import parse_qs, urlparse, unquote

import pandas as pd


class ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """多线程 HTTP 服务器 —— SSE 长连接不阻塞其他请求。"""
    allow_reuse_address = True
    daemon_threads = True

from .collect import collect_city as _collect_city, _extract_gap_years, _extract_gap_districts
from .gap import build_city_gap
from .dashboard import build_dashboard_html

HOST = "127.0.0.1"
PORT = 8765

# ── 模板 ──
_TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
INDEX_HTML = (_TEMPLATE_DIR / "index.html").read_text(encoding="utf-8")

# ── 缓存目录 ──
_CACHE_DIR = Path(__file__).resolve().parents[1] / "outputs" / "cache"
_CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _kill_existing(port: int):
    """尝试杀掉占用端口的旧进程。"""
    import subprocess
    try:
        if os.name == "nt":
            out = subprocess.check_output(f'netstat -ano | findstr ":{port}"',
                                          shell=True, text=True)
            pids = set()
            for line in out.strip().split('\n'):
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in line:
                    pids.add(parts[-1])
            for pid in pids:
                subprocess.run(f"taskkill /F /PID {pid}", shell=True,
                               capture_output=True, timeout=3)
        else:
            out = subprocess.check_output(f"lsof -ti:{port}", shell=True, text=True)
            for pid in out.strip().split('\n'):
                os.kill(int(pid), signal.SIGKILL)
    except Exception:
        pass


def _list_cached() -> list[dict]:
    """列出已缓存的城市结果。"""
    cached = []
    for f in sorted(_CACHE_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_file"] = f.name
            cached.append(data)
        except Exception:
            pass
    return cached


def _save_cache(city: str, province: str, html: str, csv_data: str, gap_summary: dict):
    """保存采集结果到缓存。"""
    import hashlib
    import numpy as np
    def _safe(obj):
        if isinstance(obj, dict): return {k: _safe(v) for k,v in obj.items()}
        if isinstance(obj, list): return [_safe(v) for v in obj]
        if isinstance(obj, (np.bool_,)): return bool(obj)
        if isinstance(obj, (np.integer,)): return int(obj)
        if isinstance(obj, (np.floating,)): return float(obj)
        return obj
    key = hashlib.md5(f"{province}_{city}".encode()).hexdigest()[:8]
    cache_file = _CACHE_DIR / f"{key}_{city}.json"
    cache_file.write_text(json.dumps(_safe({
        "city": city, "province": province,
        "html": html, "csv": csv_data,
        "summary": _safe(gap_summary),
        "cached_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
    }), ensure_ascii=False), encoding="utf-8")


class AgentHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path in ("/", "/index.html"):
            self._serve_html(INDEX_HTML)

        elif parsed.path == "/api/cached":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            cached = _list_cached()
            # 返回摘要（不包含完整 HTML，太大）
            summary = [{"city": c["city"], "province": c["province"],
                        "summary": c.get("summary", {}), "cached_at": c.get("cached_at", ""),
                        "_file": c["_file"]} for c in cached]
            self.wfile.write(json.dumps(summary, ensure_ascii=False).encode("utf-8"))

        elif parsed.path.startswith("/api/cached/"):
            filename = unquote(parsed.path.split("/")[-1])
            cache_file = _CACHE_DIR / filename
            if cache_file.exists():
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")

        elif parsed.path == "/api/collect":
            qs = parse_qs(parsed.query)
            city = qs.get("city", [""])[0]
            province = qs.get("province", [""])[0]
            self._handle_collect_sse(city, province)

        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")

    def _serve_html(self, html: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _sse(self, event: str, data: dict):
        payload = json.dumps(data, ensure_ascii=False)
        msg = f"event: {event}\ndata: {payload}\n\n"
        self.wfile.write(msg.encode("utf-8"))
        self.wfile.flush()

    def _handle_collect_sse(self, city: str, province: str):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        try:
            # 先做缺口诊断，用于定向搜索
            self._sse("progress", {"msg": "缺口诊断...", "level": "info", "stage": "search", "pct": 3, "label": "缺口诊断"})
            gap = build_city_gap(city, province)
            gap_years = _extract_gap_years(gap)
            gap_dists = _extract_gap_districts(gap)
            if gap_years or gap_dists:
                self._sse("progress", {"msg": f"缺口: 年份{len(gap_years)}处, 区县{len(gap_dists)}处 — 定向检索", "level": "warn", "pct": 5})
            self._sse("progress", {"msg": "搜狗微信多源搜索...", "level": "info", "stage": "search", "pct": 8, "label": "搜索中"})
            df = _collect_city(province, city, use_llm=True, max_queries=3, gap_data=gap)
            n_total = len(df)
            self._sse("progress", {"msg": f"搜索完成: {n_total} 条", "level": "ok", "pct": 30, "stage_done": "search"})

            self._sse("progress", {"msg": "V5 预筛选...", "level": "info", "stage": "screen", "pct": 35, "label": "预筛选"})
            n_pass = len(df[df["verdict"] == "PASS"]) if n_total > 0 else 0
            n_llm = len(df[df["verdict"] == "LLM_PASS"]) if n_total > 0 else 0
            self._sse("progress", {"msg": f"PASS {n_pass} + LLM_PASS {n_llm} / {n_total}", "level": "ok", "pct": 50, "stage_done": "screen"})

            self._sse("progress", {"msg": "去重比对...", "level": "info", "stage": "dedup", "pct": 55, "label": "去重"})
            self._sse("progress", {"msg": "去重完成", "level": "ok", "pct": 60, "stage_done": "dedup"})

            self._sse("progress", {"msg": f"缺口诊断: {city}", "level": "info", "stage": "gap", "pct": 65, "label": "诊断"})
            s = gap["summary"]
            pending_n = len(gap.get("pending_files", []))
            self._sse("progress", {"msg": f"市级 {s['city_level_n']}条 ({s['year_range_city']}) | 区级 {s['district_n']}条 ({s['year_range_district']})" + (f" | 待入库 {pending_n}个文件" if pending_n else ""), "level": "ok", "pct": 82, "stage_done": "gap"})

            self._sse("progress", {"msg": "生成交互看板...", "level": "info", "stage": "done", "pct": 90, "label": "看板"})
            candidates = []
            keep_df = df[df["verdict"].isin(["PASS", "LLM_PASS"])] if n_total > 0 else df
            for _, r in keep_df.iterrows():
                candidates.append({
                    "title": str(r.get("title", ""))[:200], "url": str(r.get("url", "")),
                    "pkulaw_link": str(r.get("pkulaw_link", "")) if "pkulaw_link" in keep_df.columns else "",
                    "flk_link": str(r.get("flk_link", "")) if "flk_link" in keep_df.columns else "",
                    "kw_score": int(r.get("kw_score", 0)) if pd.notna(r.get("kw_score")) else 0,
                    "verdict": str(r.get("verdict", "")), "reason": str(r.get("reason", "")),
                })
            df_csv = df.to_csv(index=False) if n_total > 0 else ""
            html = build_dashboard_html(gap, candidates)

            # 缓存结果
            _save_cache(city, province, html, df_csv, s)

            self._sse("progress", {"msg": f"完成! {len(candidates)} 条候选", "level": "ok", "pct": 100, "stage_done": "done"})
            self._sse("dashboard", {"html": html, "csv": df_csv, "n_candidates": len(candidates)})

        except Exception as e:
            import traceback
            self._sse("progress", {"msg": f"错误: {traceback.format_exc()[-300:]}", "level": "error"})
            self._sse("done", {"status": "error", "error": str(e)})


def start_server(host: str = HOST, port: int = PORT):
    _kill_existing(port)
    server = ThreadingHTTPServer((host, port), AgentHandler)

    url = f"http://{host}:{port}"
    print(f"\n  GGF-TWI Agent: {url}")
    print(f"  按 Ctrl+C 停止。\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  已停止。")
        server.server_close()


if __name__ == "__main__":
    port = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--port" else PORT
    start_server(HOST, port)
