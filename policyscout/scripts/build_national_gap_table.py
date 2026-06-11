# DEPRECATED — use policyscout package instead (from policyscout.xxx import ...)
"""
全国缺口表生成器 — 从主 flat 生成最新缺口表。

运行: python scripts/agent/build_national_gap_table.py

输出 (outputs/agent/):
  - national_gap_cities.csv      全国城市级缺口（P0/P1 优先级 + 检索式）
  - national_gap_provinces.csv   省级汇总（覆盖率分层）
  - national_gap_summary.csv     简短摘要
"""
from __future__ import annotations

import argparse
from datetime import datetime as dt
from pathlib import Path

import pandas as pd

from config import (
    MAIN_FLAT, OUTPUTS_DIR, INST_TYPES, PROVINCES,
    MUNICIPALITIES, PREFECTURE_COUNTS,
    L2_MIN_COVERAGE_PCT, L2_MIN_CITIES, GGF_TWI_MIN_INST,
    SEARCH_TEMPLATES,
)


def build_gap_tables(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """返回 (province_summary, city_gap_table)。"""

    # ── 筛选制度文本 ──
    inst_mask = df["doc_type"].isin(INST_TYPES)
    inst = df[inst_mask].copy()

    # ── 省级汇总 ──
    prov_rows = []
    for prov in PROVINCES:
        prov_inst = inst[inst["province"] == prov]
        prov_all = df[df["province"] == prov]

        # 有制度文本的地级市（排除省级文本的 city=NaN）
        cities_with_inst = prov_inst[prov_inst["city"].notna() & (prov_inst["city"].astype(str).str.strip() != "")]

        # 唯一城市数（规范化：去重 city）
        unique_cities = set()
        for c in cities_with_inst["city"]:
            c_str = str(c).strip()
            if c_str and "、" not in c_str and "，" not in c_str:
                unique_cities.add(c_str)

        n_cities = len(unique_cities)
        n_inst = len(prov_inst)
        n_all = len(prov_all)
        n_total_pref = PREFECTURE_COUNTS.get(prov, 0)

        coverage_pct = round(n_cities / n_total_pref * 100, 1) if n_total_pref > 0 else 0

        # 分层
        if prov in MUNICIPALITIES:
            tier = "N/A (直辖市)"
        elif n_cities == 0:
            tier = "L0-空白"
        elif coverage_pct >= 50 and n_cities >= 3:
            tier = "L3-高覆盖"
        elif coverage_pct >= L2_MIN_COVERAGE_PCT or n_cities >= L2_MIN_CITIES:
            tier = "L2-中等覆盖"
        elif coverage_pct < L2_MIN_COVERAGE_PCT and n_cities < L2_MIN_CITIES:
            if n_cities == 0:
                tier = "L0-空白"
            else:
                tier = "L1-低覆盖"
        else:
            tier = "L1-低覆盖"

        # 缺口：L2 线 = 覆盖率 ≥ 30% OR ≥ 5 城
        if prov in MUNICIPALITIES:
            gap_priority = ""
            cities_to_l2 = 0
        elif coverage_pct >= L2_MIN_COVERAGE_PCT or n_cities >= L2_MIN_CITIES:
            gap_priority = ""
            cities_to_l2 = 0
        elif n_cities == 0:
            gap_priority = "P0"
            cities_to_l2 = max(L2_MIN_CITIES, int(n_total_pref * L2_MIN_COVERAGE_PCT / 100))
        else:
            # 距 L2 线还需要多少城市（取两条路径中较近的一条）
            needed_30pct = max(0, int(n_total_pref * L2_MIN_COVERAGE_PCT / 100) - n_cities + 1)
            needed_5 = max(0, L2_MIN_CITIES - n_cities)
            cities_to_l2 = min(needed_30pct, needed_5) if needed_30pct > 0 and needed_5 > 0 else max(needed_30pct, needed_5)
            # P0: ≤2 城市 且 覆盖率 < 30%（数据极度稀缺，优先采集）
            if n_cities <= 2:
                gap_priority = "P0"
            elif cities_to_l2 > 2:
                gap_priority = "P0"
            else:
                gap_priority = "P1"

        prov_rows.append({
            "province": prov,
            "pref_divisions": n_total_pref,
            "cities_with_inst": n_cities,
            "n_inst_texts": n_inst,
            "n_all_texts": n_all,
            "coverage_pct": coverage_pct,
            "L_tier": tier,
            "gap_priority": gap_priority,
            "cities_to_L2": cities_to_l2,
            "has_prov_inst": len(prov_inst[prov_inst["policy_level"].astype(str).str.strip() == "省级"]) > 0,
        })

    prov_df = pd.DataFrame(prov_rows).sort_values(
        ["gap_priority", "coverage_pct"],
        ascending=[True, True]
    )

    # ── 城市级缺口表 ──
    city_rows = []

    inst_with_city = inst[inst["city"].notna() & (inst["city"].astype(str).str.strip() != "")]
    city_stats = inst_with_city.groupby(["province", "city"]).agg(
        n_inst=("source_id", "nunique"),
        year_min=("year", "min"),
        year_max=("year", "max"),
    ).reset_index()

    # 聚合：每个省的城市列表
    for prov in PROVINCES:
        if prov in MUNICIPALITIES:
            continue  # 直辖市另有逻辑

        prov_cities = city_stats[city_stats["province"] == prov]
        n_total_pref = PREFECTURE_COUNTS.get(prov, 0)
        n_cities_with_inst = prov_cities["city"].nunique()

        # 所有城市
        for _, r in prov_cities.iterrows():
            city = r["city"]
            n_i = int(r["n_inst"])

            # 生成检索式
            queries = []
            for name, tmpl in SEARCH_TEMPLATES.items():
                queries.append(tmpl.replace("{city}", city))

            # 入选状态
            in_ggf_twi = n_i >= GGF_TWI_MIN_INST

            city_rows.append({
                "province": prov,
                "city": city,
                "n_inst": n_i,
                "year_range": f"{int(r['year_min'])}-{int(r['year_max'])}" if pd.notna(r["year_min"]) else "",
                "in_ggf_twi": in_ggf_twi,
                "pref_divisions_in_prov": n_total_pref,
                "prov_coverage_pct": round(n_cities_with_inst / n_total_pref * 100, 1) if n_total_pref > 0 else 0,
                "prov_L_tier": prov_df[prov_df["province"] == prov]["L_tier"].values[0] if len(prov_df[prov_df["province"] == prov]) else "",
                "suggested_queries": " | ".join(queries[:3]),  # 前 3 条
            })

    city_df = pd.DataFrame(city_rows).sort_values(
        ["province", "n_inst"],
        ascending=[True, False]
    )

    return prov_df, city_df


def main():
    parser = argparse.ArgumentParser(description="生成全国采集缺口表")
    parser.add_argument("--input-csv", type=str, default=str(MAIN_FLAT))
    parser.add_argument("--output-dir", type=str, default=str(OUTPUTS_DIR))
    args = parser.parse_args()

    print(f"[INFO] 读取: {args.input_csv}")
    df = pd.read_csv(args.input_csv)
    print(f"[INFO] {len(df)} 行, {df['doc_type'].isin(INST_TYPES).sum()} 条制度文本")

    prov_df, city_df = build_gap_tables(df)

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)

    # 写入省级汇总
    prov_path = outdir / "national_gap_provinces.csv"
    prov_df.to_csv(prov_path, index=False)
    print(f"[DONE] 省级汇总: {prov_path}")

    # 写入城市缺口
    city_path = outdir / "national_gap_cities.csv"
    city_df.to_csv(city_path, index=False)
    print(f"[DONE] 城市缺口表: {city_path}")

    # 简短摘要
    p0_provs = prov_df[prov_df["gap_priority"] == "P0"]
    p1_provs = prov_df[prov_df["gap_priority"] == "P1"]
    l0_provs = prov_df[prov_df["L_tier"] == "L0-空白"]

    ts = dt.now().strftime("%Y-%m-%d %H:%M")
    summary_lines = [
        f"# 全国采集缺口摘要 — {ts}",
        "",
        "## P0 缺口省",
        f"共 {len(p0_provs)} 省 (覆盖率 < 30% 且 < 5 城):",
    ]
    for _, r in p0_provs.iterrows():
        summary_lines.append(
            f"- **{r['province']}**: {int(r['cities_with_inst'])}/{int(r['pref_divisions'])}={r['coverage_pct']}%, "
            f"距L2差 {int(r['cities_to_L2'])} 城, {int(r['n_inst_texts'])} 条制度"
        )

    summary_lines.append("")
    summary_lines.append("## P1 缺口省")
    for _, r in p1_provs.iterrows():
        summary_lines.append(
            f"- {r['province']}: {int(r['cities_with_inst'])}/{int(r['pref_divisions'])}={r['coverage_pct']}%, "
            f"距L2差 {int(r['cities_to_L2'])} 城"
        )

    summary_lines.append("")
    summary_lines.append("## 省级文本缺失")
    for _, r in prov_df[~prov_df["has_prov_inst"]].iterrows():
        summary_lines.append(f"- {r['province']}: 无省级制度文本")

    summary_path = outdir / "national_gap_summary.md"
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")
    print(f"[DONE] 摘要: {summary_path}")
    print("\n".join(summary_lines))


if __name__ == "__main__":
    main()
