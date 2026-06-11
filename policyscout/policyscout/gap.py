"""城市制度文本缺口分析引擎 — 数据库 + intake 目录全量扫描。"""
from __future__ import annotations

import pandas as pd
import numpy as np
from collections import defaultdict

from .config import MAIN_FLAT, INTAKE_DATA_DIR, INST_TYPES, CORE8, MUNICIPALITIES


def is_hit(v) -> bool:
    return pd.notna(v) and str(v).strip() not in ("", "0", "no", "0.0", "False", "None")


def build_city_gap(city: str, province: str = "") -> dict:
    """
    单城市制度文本缺口诊断 — 扫描主 flat（已入库） + intake 目录（待入库）。

    Returns dict with summary, city_texts, district_texts, year_timeline,
    provincial_context, pending_files.
    """
    df = pd.read_csv(MAIN_FLAT)
    is_municipality = city in MUNICIPALITIES

    # ── 已入库：本城市所有记录 ──
    city_all = df[(df["city"] == city) & (df["is_national"] == 0)].copy()
    city_inst = city_all[city_all["doc_type"].isin(INST_TYPES)].copy()

    # 直辖市：省级文本（city字段为空，通过province匹配）计入城市本级
    if is_municipality:
        city_prov = df[(df["province"] == city) &
                       (df["policy_level"] == "省级") &
                       (df["is_national"] == 0)].copy()
        city_prov_inst = city_prov[city_prov["doc_type"].isin(INST_TYPES)]
        city_inst = pd.concat([city_inst, city_prov_inst])
        city_all = pd.concat([city_all, city_prov])
    else:
        city_prov = pd.DataFrame()
        city_prov_inst = pd.DataFrame()

    # ── 省级制度文本（本省，直辖市不重复）──
    if province and not is_municipality:
        prov_all = df[(df["province"] == province) &
                      (df["policy_level"] == "省级") &
                      (df["is_national"] == 0)].copy()
        prov_inst = prov_all[prov_all["doc_type"].isin(INST_TYPES)]
    elif is_municipality:
        prov_all = pd.DataFrame()
        prov_inst = pd.DataFrame()
    else:
        prov_all = df[(df["province"] == city) &
                      (df["policy_level"] == "省级") &
                      (df["is_national"] == 0)].copy()
        prov_inst = prov_all[prov_all["doc_type"].isin(INST_TYPES)]

    # ── 分类统计 ──
    city_level_all = city_all[city_all["policy_level"].isin(["市级"] + (["省级"] if is_municipality else []))]
    city_level_inst = city_level_all[city_level_all["doc_type"].isin(INST_TYPES)]
    district_all = city_all[city_all["policy_level"] == "区县级"]
    district_inst = district_all[district_all["doc_type"].isin(INST_TYPES)]

    # 常见区级关键词
    _DISTRICT_KW = ["区", "新区", "开发区", "街道", "镇"]
    _is_district_title = lambda t: any(kw in str(t) and "地区" not in str(t) and "区域" not in str(t) for kw in _DISTRICT_KW)

    def build_rows(data, level=""):
        rows = []
        for _, r in data.iterrows():
            hits = sum(1 for f in CORE8 if is_hit(r.get(f)))
            issues = []
            title = str(r.get("title", ""))
            if hits == 0 and r.get("year", 9999) < 2012:
                issues.append("旧文本(<=2011)")
            if "税" in str(title) and "引导基金" not in str(title):
                issues.append("分类错误")
            if level == "市级" and _is_district_title(title):
                issues.append("含区级地名")
            rows.append({
                "source_id": int(r["source_id"]) if pd.notna(r.get("source_id")) else None,
                "title": str(r.get("title", ""))[:200],
                "year": int(r["year"]) if pd.notna(r.get("year")) else None,
                "doc_type": str(r.get("doc_type", "")),
                "policy_level": str(r.get("policy_level", "")),
                "hits": hits,
                "fields": {f: {"value": str(r.get(f, "nan"))[:40], "hit": bool(is_hit(r.get(f)))} for f in CORE8},
                "issues": issues,
                "source_level": str(r.get("policy_level", "")),  # 原始 policy_level
            })
        return rows

    city_rows = build_rows(city_level_inst, "市级")
    district_rows = build_rows(district_inst, "区级")
    prov_rows = build_rows(prov_inst, "省级")

    # ── 年份时间线 ──
    years = defaultdict(lambda: {"市级": 0, "区县级": 0})
    for _, r in city_level_inst.iterrows():
        yr = int(r["year"]) if pd.notna(r.get("year")) else None
        if yr: years[yr]["市级"] += 1
    for _, r in district_inst.iterrows():
        yr = int(r["year"]) if pd.notna(r.get("year")) else None
        if yr: years[yr]["区县级"] += 1
    timeline = [{"year": y, **c} for y, c in sorted(years.items())]

    # ── 扫描 intake 目录（文件名 + 内容前 500 字）──
    pending_files = []
    search_terms = [city, city.replace("市", ""), city.replace("省", "")]
    if province:
        search_terms.extend([province, province.replace("省", ""), province.replace("市", "")])
    search_terms = [t for t in set(search_terms) if len(t) >= 2]

    if INTAKE_DATA_DIR.exists():
        for f in INTAKE_DATA_DIR.rglob("*.md"):
            if "_manifest" in str(f) or "_原文" in str(f) or ".cleaned" in str(f):
                continue
            fname = f.stem
            fpath = str(f.relative_to(INTAKE_DATA_DIR))
            # Check filename first
            matched = any(t in fname for t in search_terms)
            # Also check first 500 chars of content
            if not matched:
                try:
                    head = f.read_text(encoding="utf-8")[:500]
                    matched = any(t in head for t in search_terms)
                except Exception:
                    pass
            if matched:
                try:
                    first_line = f.read_text(encoding="utf-8")[:200].split('\n')[0].strip()
                except Exception:
                    first_line = fname
                pending_files.append({
                    "filename": fname, "path": fpath,
                    "preview": first_line[:100],
                })

    # ── 热力图数据：市本级 + 各区县 × 年（基于 district_county 字段）──
    heatmap_rows = []
    # 市本级行：district_county 为空的文本
    city_years = defaultdict(int)
    for _, r in city_level_inst.iterrows():
        if pd.isna(r.get("district_county")) or str(r.get("district_county")).strip() == "":
            yr = int(r["year"]) if pd.notna(r.get("year")) else None
            if yr: city_years[yr] += 1
    heatmap_rows.append({"label": city + " 市本级", "type": "市级", "years": dict(city_years)})

    # 各区县行：基于 district_county 字段
    all_texts = pd.concat([city_inst, city_all]).drop_duplicates(subset=["source_id"])
    district_map = defaultdict(lambda: defaultdict(int))
    for _, r in all_texts.iterrows():
        dc = str(r.get("district_county", "")).strip() if pd.notna(r.get("district_county")) else ""
        if not dc or dc == "nan":
            continue
        yr = int(r["year"]) if pd.notna(r.get("year")) else None
        if yr:
            district_map[dc][yr] += 1
    for dist in sorted(district_map.keys())[:30]:
        heatmap_rows.append({"label": dist, "type": "区县", "years": dict(district_map[dist])})

    # ── 省级上下文 ──
    prov_ctx = None
    if len(prov_inst) > 0:
        scores = []
        for _, r in prov_inst.iterrows():
            m = sum(1 for f in CORE8[:4] if is_hit(r.get(f))) / 4
            r_ = sum(1 for f in CORE8[4:6] if is_hit(r.get(f))) / 2
            v = sum(1 for f in CORE8[6:8] if is_hit(r.get(f))) / 2
            scores.append((m + r_ + v) / 3)
        prov_ctx = {
            "n_texts": int(len(prov_inst)),
            "pmi": round(float(np.mean(scores)), 4) if scores else None,
            "year_min": int(prov_inst["year"].min()) if "year" in prov_inst.columns and prov_inst["year"].notna().any() else None,
            "year_max": int(prov_inst["year"].max()) if "year" in prov_inst.columns and prov_inst["year"].notna().any() else None,
        }

    return {
        "city": city,
        "province": province or "",
        "summary": {
            "city_level_n": len(city_level_inst),
            "city_level_total": len(city_level_all),
            "district_n": len(district_inst),
            "district_total": len(district_all),
            "provincial_n": len(prov_inst),
            "provincial_total": len(prov_all),
            "is_municipality": bool(is_municipality),
            "year_range_city": f"{int(city_level_inst['year'].min())}-{int(city_level_inst['year'].max())}" if len(city_level_inst) > 0 and city_level_inst["year"].notna().any() else "-",
            "year_range_district": f"{int(district_inst['year'].min())}-{int(district_inst['year'].max())}" if len(district_inst) > 0 and district_inst["year"].notna().any() else "-",
            "gap_years": "2012-2026" if (len(city_level_inst) > 0 and city_level_inst["year"].max() < 2012) or len(city_level_inst) == 0 else "-",
            "has_gap": (len(city_level_inst) > 0 and city_level_inst["year"].max() < 2012) or len(city_level_inst) == 0,
            "city_level_total_hits": sum(r["hits"] for r in city_rows),
            "district_total_hits": sum(r["hits"] for r in district_rows),
        },
        "city_texts": city_rows,
        "district_texts": district_rows,
        "provincial_texts": prov_rows,
        "pending_files": pending_files,
        "heatmap": heatmap_rows,
        "year_timeline": timeline,
        "provincial_context": prov_ctx,
    }
