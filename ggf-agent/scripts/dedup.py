# DEPRECATED — use ggf_agent package instead (from ggf_agent.xxx import ...)
"""
全国范围全局去重引擎。

检测三类重复：
1. doc_number 精确匹配（主去重键）
2. URL 精确匹配
3. 标题 Jaccard 相似度 ≥ 0.85

输出: outputs/agent/global_duplicates.csv（标注 canonical_source_id，不自动删除）

可被其他脚本 import 使用:
    from scripts.agent.dedup import find_duplicates, generate_dedup_report
"""
from __future__ import annotations

import argparse
from datetime import datetime as dt
from pathlib import Path

import pandas as pd

from config import MAIN_FLAT, OUTPUTS_DIR, INST_TYPES


def jaccard_similarity(s1: str, s2: str) -> float:
    """两个字符串的字符级 Jaccard 相似度（快速）。"""
    set1, set2 = set(s1), set(s2)
    if not set1 or not set2:
        return 0.0
    return len(set1 & set2) / len(set1 | set2)


def find_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    全局去重。返回重复组 DataFrame，每行一个重复关系。
    列: source_id, dup_source_id, dup_type, similarity, canonical_source_id, notes
    """
    records: list[dict] = []

    # ── 1. doc_number 精确匹配 ──
    dn = df[df["doc_number"].notna() & (df["doc_number"].astype(str).str.strip() != "")].copy()
    dn["doc_number_clean"] = dn["doc_number"].astype(str).str.strip()
    dup_dn = dn.groupby("doc_number_clean").filter(lambda g: len(g) > 1)
    if len(dup_dn):
        for doc_num, group in dup_dn.groupby("doc_number_clean"):
            ids = sorted(group["source_id"].tolist())
            canonical = ids[0]  # 最小 source_id 为 canonical
            for sid in ids[1:]:
                records.append({
                    "source_id": canonical,
                    "dup_source_id": sid,
                    "dup_type": "doc_number",
                    "similarity": 1.0,
                    "canonical_source_id": canonical,
                    "doc_number": doc_num,
                    "notes": f"同文号: {doc_num}",
                })

    # ── 2. URL 精确匹配 ──
    url = df[df["url"].notna() & (df["url"].astype(str).str.strip() != "")].copy()
    url["url_clean"] = url["url"].astype(str).str.strip()
    dup_url = url.groupby("url_clean").filter(lambda g: len(g) > 1)
    if len(dup_url):
        for url_val, group in dup_url.groupby("url_clean"):
            ids = sorted(group["source_id"].tolist())
            canonical = ids[0]
            for sid in ids[1:]:
                records.append({
                    "source_id": canonical,
                    "dup_source_id": sid,
                    "dup_type": "url",
                    "similarity": 1.0,
                    "canonical_source_id": canonical,
                    "doc_number": "",
                    "notes": f"同URL: {url_val[:80]}...",
                })

    # ── 3. 标题相似度（Jaccard ≥ 0.85）──
    # 仅在相同 province + city 且相同 doc_type 范围内比较，避免跨城市误匹配
    titles = df[df["title"].notna()].copy()
    titles["title_clean"] = titles["title"].astype(str).str.strip()
    titles = titles[titles["title_clean"] != ""]

    # 按 (province, city, doc_type) 分组
    titles["_group_key"] = (
        titles["province"].fillna("").astype(str) + "|" +
        titles["city"].fillna("").astype(str) + "|" +
        titles["doc_type"].fillna("").astype(str)
    )
    for _, group in titles.groupby("_group_key"):
        if len(group) <= 1:
            continue
        ids = group["source_id"].tolist()
        title_dict = dict(zip(group["source_id"], group["title_clean"]))
        n = len(ids)
        for i in range(n):
            for j in range(i + 1, n):
                si, sj = ids[i], ids[j]
                ti, tj = title_dict[si], title_dict[sj]
                sim = jaccard_similarity(ti, tj)
                if sim >= 0.85:
                    canonical = min(si, sj)
                    other = max(si, sj)
                    records.append({
                        "source_id": canonical,
                        "dup_source_id": other,
                        "dup_type": "title_similar",
                        "similarity": round(sim, 4),
                        "canonical_source_id": canonical,
                        "doc_number": "",
                        "notes": f"标题相似: {ti[:60]} ≈ {tj[:60]}",
                    })

    if not records:
        return pd.DataFrame(columns=[
            "source_id", "dup_source_id", "dup_type", "similarity",
            "canonical_source_id", "doc_number", "notes"
        ])

    result = pd.DataFrame(records).drop_duplicates(
        subset=["source_id", "dup_source_id", "dup_type"]
    )
    return result.sort_values(["dup_type", "source_id"])


def generate_dedup_report(dup_df: pd.DataFrame, main_df: pd.DataFrame) -> str:
    """生成去重摘要报告。"""
    lines = []
    lines.append(f"# 全局去重报告 — {dt.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"## 总览")
    lines.append(f"- 总行数: {len(main_df)}")
    lines.append(f"- 重复关系总数: {len(dup_df)}")

    for dtype in ["doc_number", "url", "title_similar"]:
        sub = dup_df[dup_df["dup_type"] == dtype]
        if len(sub):
            n_groups = sub["canonical_source_id"].nunique()
            n_rows = sub["dup_source_id"].nunique()
            lines.append(f"- {dtype}: {len(sub)} 对关系, {n_groups} 组, {n_rows} 条可去重")

    # 制度文本中的重复
    inst_ids = set(main_df[main_df["doc_type"].isin(INST_TYPES)]["source_id"])
    dup_inst = dup_df[dup_df["source_id"].isin(inst_ids) | dup_df["dup_source_id"].isin(inst_ids)]
    lines.append(f"\n## 制度文本重复")
    lines.append(f"- 涉及制度文本的重复关系: {len(dup_inst)}")
    lines.append(f"- 建议优先处理的制度文重复组: {dup_inst['canonical_source_id'].nunique()} 组")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="全国范围全局去重")
    parser.add_argument("--input-csv", type=str, default=str(MAIN_FLAT))
    parser.add_argument("--output-dir", type=str, default=str(OUTPUTS_DIR))
    args = parser.parse_args()

    print(f"[INFO] 读取: {args.input_csv}")
    df = pd.read_csv(args.input_csv)
    print(f"[INFO] {len(df)} 行")

    dup_df = find_duplicates(df)
    print(f"[INFO] 发现 {len(dup_df)} 条重复关系")

    outdir = Path(args.output_dir)
    outdir.mkdir(parents=True, exist_ok=True)
    outpath = outdir / "global_duplicates.csv"
    dup_df.to_csv(outpath, index=False)
    print(f"[INFO] 重复详情: {outpath}")

    report = generate_dedup_report(dup_df, df)
    report_path = outdir / "global_duplicates_report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"[INFO] 报告: {report_path}")
    print(report)


if __name__ == "__main__":
    main()
