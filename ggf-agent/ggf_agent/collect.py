"""城市采集编排器 — 多源搜索 + V5预筛选 + 智能去重 + 保存候选列表。"""
from __future__ import annotations

import re
import time
from datetime import datetime as dt
from pathlib import Path

import pandas as pd

from .config import MAIN_FLAT, CANDIDATES_DIR, SEARCH_DELAY, PROJECT_ROOT, ENABLE_BING
from .search_sogou import search_sogou_weixin
from .prescreen import prescreen


def extract_policy_names(title: str) -> list[str]:
    """从标题中提取《》内的政策名称。"""
    return re.findall(r'《([^》]+)》', str(title))


def dedup_by_policy_name(
    candidates: list[dict],
    existing_titles: set[str],
) -> list[dict]:
    """
    智能去重：若候选标题中《》内的政策名称（≥4 字）在已有标题中
    作为子串出现，标记为 REJECT / DUP_EXISTING。

    典型场景：搜狗微信结果中的"发改委印发《政府出资产业投资基金
    管理暂行办法》"与主 flat 中"国家发展改革委关于印发《政府出资
    产业投资基金管理暂行办法》的通知"指向同一份国家级文件。
    """
    for r in candidates:
        if r.get("verdict") == "REJECT":
            continue
        policy_names = extract_policy_names(r.get("title", ""))
        for pn in policy_names:
            if len(pn) < 4:       # 过短的政策名不判重（避免误匹配）
                continue
            for et in existing_titles:
                if pn in str(et):
                    r["verdict"] = "REJECT"
                    r["reason"] = "DUP_EXISTING"
                    break
    return candidates


def _extract_gap_years(gap_data: dict) -> list[int]:
    """从缺口数据中提取市级文本覆盖为 0 的年份。"""
    tl = gap_data.get("year_timeline", [])
    if not tl:
        return []
    years = sorted(y["year"] for y in tl)
    if not years:
        return []
    gap_years = []
    for yr in range(years[0], years[-1] + 1):
        entry = next((y for y in tl if y["year"] == yr), None)
        city_n = entry["市级"] if entry else 0
        if city_n == 0 and yr >= 2012:  # 2012年后市级文本为0 = 缺口
            gap_years.append(yr)
    return gap_years


def _extract_gap_districts(gap_data: dict) -> list[str]:
    """从缺口数据中提取覆盖为 0 的区县。"""
    hm = gap_data.get("heatmap", [])
    if not hm:
        return []
    gaps = []
    for row in hm:
        if row.get("type") == "区县" and row.get("label"):
            years = row.get("years", {})
            if not years or len(years) <= 1:
                gaps.append(row["label"])
    return gaps[:5]


def collect_city(province: str, city: str, use_llm: bool = True,
                 max_queries: int = 3, gap_data: dict = None) -> pd.DataFrame:
    """
    单城市采集：多检索式搜索 → V5预筛选 → 智能去重 → 保存。

    Args:
        province: 省名
        city: 城市名
        use_llm: 是否对边际结果调 LLM 分类
        max_queries: 最多几种检索式
        gap_data: 缺口诊断数据（build_city_gap 输出），用于定向搜索

    Returns:
        候选 DataFrame（含 verdict 列）
    """
    # 构建检索式：缺口定向 query 优先
    queries = []
    if gap_data:
        # 缺口年份定向
        gap_years = _extract_gap_years(gap_data)
        for yr in gap_years[:2]:
            queries.append(f"{city} {yr} 引导基金 管理办法")
        # 缺口区县定向
        gap_districts = _extract_gap_districts(gap_data)
        for d in gap_districts[:3]:
            queries.append(f"{city} {d} 引导基金 管理办法")
        if gap_years or gap_districts:
            print(f"  缺口定向检索: {len(queries)} 条 (年={gap_years[:2]}, 区={gap_districts[:3]})")

    # 通用检索补充
    generic = [
        f"{city} 引导基金 管理办法",
        f"{city} 产业投资基金 暂行办法",
        f"{city} 政府投资基金 管理",
    ]
    queries.extend(generic)
    # 去重并限制数量
    seen = set()
    queries = [q for q in queries if not (q in seen or seen.add(q))]
    max_q = max(max_queries, 5) if gap_data else max_queries
    queries = queries[:max_q]

    all_results: list[dict] = []
    seen_titles: set[str] = set()

    for qi, query in enumerate(queries):
        # 搜狗微信
        print(f"  [{qi+1}/{len(queries)}] 搜狗: {query}")
        results = search_sogou_weixin(query)
        for r in results:
            key = r["title"].strip()
            if key not in seen_titles:
                seen_titles.add(key)
                r["search_query"] = f"sogou:{query}"
                all_results.append(r)
        time.sleep(SEARCH_DELAY)

        # Bing（默认关闭—gov.cn命中率极低）
        if ENABLE_BING:
            from .search_bing import search_bing
            print(f"  [{qi+1}/{len(queries)}] Bing: {query} site:gov.cn")
            for r in search_bing(query, count=10):
                key = r["title"].strip()
                if key not in seen_titles:
                    seen_titles.add(key)
                    r["search_query"] = f"bing:{query}"
                    all_results.append(r)
            time.sleep(SEARCH_DELAY)

    if not all_results:
        print("  → 无任何结果")
        return pd.DataFrame()

    # ── V5 预筛选 ──
    print(f"  V5预筛选 {len(all_results)} 条...")
    passed, llm_passed, rejected = [], [], []

    for r in all_results:
        verdict, kw_score, reason = prescreen(
            r["title"], r.get("snippet", ""), city=city, use_llm=use_llm
        )
        r["kw_score"] = kw_score
        r["verdict"] = verdict
        r["reason"] = reason
        r["province"] = province
        r["city"] = city
        r["date_collected"] = dt.now().strftime("%Y-%m-%d")

        if verdict == "PASS":
            passed.append(r)
        elif verdict == "LLM_PASS":
            llm_passed.append(r)
        else:
            rejected.append(r)

    print(f"  PASS:{len(passed)} LLM_PASS:{len(llm_passed)} REJECT:{len(rejected)}")

    # ── 合并 PASS + LLM_PASS ──
    candidates = passed + llm_passed
    if not candidates:
        print("  → 无通过候选")
        return pd.DataFrame()

    # ── 加载已有标题（用于智能去重 + 精确排重）──
    existing_urls: set[str] = set()
    existing_titles: set[str] = set()

    # 1) 主 flat
    main_flat = pd.read_csv(MAIN_FLAT)
    existing_urls.update(main_flat["url"].dropna().astype(str).str.strip())
    existing_titles.update(main_flat["title"].dropna().astype(str).str.strip())

    # 2) intake manifest
    manifest_path = PROJECT_ROOT / "阶段1_权威数据与主库/03_待结构化增量采集_20260526/data/_manifest/intake_manifest.csv"
    if manifest_path.exists():
        mf = pd.read_csv(manifest_path)
        if "title" in mf.columns:
            existing_titles.update(mf["title"].dropna().astype(str).str.strip())

    # ── 智能去重：《》内政策名称 vs 已有标题 ──
    candidates = dedup_by_policy_name(candidates, existing_titles)
    dup_count = sum(1 for c in candidates if c.get("reason") == "DUP_EXISTING")
    if dup_count:
        print(f"  智能去重: {dup_count} 条标记为 DUP_EXISTING")

    df = pd.DataFrame(candidates)

    # 3) data/ 中已存在的 .md 文件名
    data_dir = PROJECT_ROOT / "阶段1_权威数据与主库/03_待结构化增量采集_20260526/data"
    for f in data_dir.rglob("*.md"):
        if "_manifest" not in str(f):
            existing_titles.add(f.stem.strip())

    mask_url = ~df["url"].astype(str).str.strip().isin(existing_urls)
    mask_title = ~df["title"].astype(str).str.strip().isin(existing_titles)
    df = df[mask_url & mask_title]

    # ── 保存 ──
    CANDIDATES_DIR.mkdir(parents=True, exist_ok=True)
    clean_city = city.replace("/", "_").replace("\\", "_")
    outpath = CANDIDATES_DIR / f"{province}_{clean_city}_{dt.now().strftime('%Y%m%d')}.csv"

    cols = [
        "province", "city", "source", "title", "url", "snippet",
        "search_query", "kw_score", "verdict", "reason", "date_collected",
    ]
    df[cols].to_csv(outpath, index=False, encoding="utf-8-sig")

    n_sogou = len(df[df["source"] == "sogou_weixin"])
    n_bing = len(df[df["source"] == "bing"]) if "bing" in df["source"].values else 0
    print(f"   搜狗微信: {n_sogou} 条" + (f" | Bing: {n_bing} 条" if n_bing else ""))
    print(f"  → 保存 {len(df)} 条: {outpath.name}")

    return df


if __name__ == "__main__":
    import sys
    city = sys.argv[1] if len(sys.argv) > 1 else "乌鲁木齐市"
    province = sys.argv[2] if len(sys.argv) > 2 else "新疆维吾尔自治区"
    use_llm = "--no-llm" not in sys.argv

    print(f"采集: {province} {city}")
    df = collect_city(province, city, use_llm=use_llm)

    if len(df):
        print(f"\n===== 结果预览 =====\n")
        for i, (_, r) in enumerate(df.iterrows()):
            print(f"{i+1}. [{r['verdict']}] {r['title']}")
            print(f"   URL: {r['url'][:120]}")
            print(f"   摘要: {str(r['snippet'])[:150]}")
            print()
