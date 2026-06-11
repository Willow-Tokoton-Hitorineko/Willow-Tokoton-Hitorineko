# DEPRECATED — use policyscout package instead (from policyscout.xxx import ...)
"""
V5 预筛选 — 判断搜索结果是否为有效引导基金制度文本。

复用 v5_structure_intake_with_prescreen.py 的关键词和逻辑。
规则快判不调 API；边际情况调 DeepSeek LLM 二分类（~300 tokens/条）。
"""
from __future__ import annotations

import time
from typing import Tuple

from openai import OpenAI

from config import DS_API_KEY, DS_API_BASE, DS_MODEL

# ── V5 强引导基金关键词 ──
STRONG_FUND_KW = [
    "引导基金", "产业投资基金", "创投引导", "政府投资基金",
    "天使投资引导", "产业引导基金", "创业投资引导基金",
    "容错机制", "尽职免责", "返投", "母子基金",
    "政府不干预", "管理人遴选", "绩效评价", "退出机制",
    "让利", "引导基金管理", "参股子基金", "直投",
    "投资决策委员会", "托管银行", "政府出资",
]

# ── 排除关键词（非目标文本类型）──
EXCLUDE_KW = [
    "医疗保障基金", "医保基金", "住房公积金", "维修基金",
    "百度百科", "旅游攻略", "必玩景点", "美食推荐",
]

# ── LLM 分类器 prompt ──
PRESCREEN_PROMPT = """你是政府引导基金政策文本分类器。判断以下文本是否包含政府引导基金的实质性制度内容或政策实践信号。

"实质性"是指：
- 明确的引导基金管理办法/实施细则/设立方案等制度条款
- 引导基金运作的具体信息（规模/出资/遴选/返投/容错/退出/绩效）
- 对引导基金政策执行效果的讨论（积极或消极信号均可）

排除：
- 开发区简介、一般性招商新闻，引导基金只是并列列举的一个要素
- 政府工作报告中"设立引导基金"一句话
- 笼统提及"基金"但无引导基金制度细节的文本
- PPP基金、医保基金、公积金等非引导基金文本

仅回答 YES 或 NO，不要任何解释。"""

# ── LLM 客户端（惰性初始化）──
_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=DS_API_KEY, base_url=DS_API_BASE)
    return _client


def rule_prescreen(title: str, snippet: str = "", city: str = "") -> Tuple[str, int]:
    """
    规则快判。返回 (verdict, kw_score)。
    verdict: PASS / REJECT / MARGINAL
    """
    text = title + " " + snippet

    # 排除检查
    for kw in EXCLUDE_KW:
        if kw in text:
            return "REJECT", 0

    kw_score = sum(1 for kw in STRONG_FUND_KW if kw in text)

    # 城市相关性：如果指定了城市，文本必须提及该城市或其简称
    if city and len(city) >= 2:
        city_short = city.rstrip("市区县州盟")
        if city_short not in text and city not in text:
            # 全国性政策重发（发改委/财政部/国务院），与目标城市无关
            national_indicators = ["国家发展改革委", "财政部", "国务院", "发改财金规"]
            if any(kw in text for kw in national_indicators):
                return "REJECT", 0
            # 完全不提及目标城市 → 降为 MARGINAL
            if kw_score >= 2:
                return "MARGINAL", kw_score

    if kw_score >= 2:
        return "PASS", kw_score
    if len(text) < 80 and kw_score == 0:
        return "REJECT", kw_score
    return "MARGINAL", kw_score


def llm_prescreen(title: str, snippet: str = "", max_retries: int = 2) -> Tuple[bool, str]:
    """
    LLM 二分类器。返回 (pass, reason)。
    成本 ~300 tokens/条。
    """
    text = f"标题：{title}\n\n内容摘要：{snippet[:3000]}"

    for attempt in range(max_retries):
        try:
            client = _get_client()
            resp = client.chat.completions.create(
                model=DS_MODEL,
                messages=[
                    {"role": "system", "content": PRESCREEN_PROMPT},
                    {"role": "user", "content": text},
                ],
                max_tokens=10,
                temperature=0,
            )
            answer = resp.choices[0].message.content.strip().upper()
            if "YES" in answer:
                return True, "LLM_YES"
            return False, "LLM_NO"
        except Exception as exc:
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                return False, f"LLM_ERROR:{exc}"

    return False, "LLM_UNKNOWN"


def prescreen(title: str, snippet: str = "", city: str = "", use_llm: bool = True) -> Tuple[str, int, str]:
    """
    完整预筛选。返回 (verdict, kw_score, reason)。
    verdict: PASS / REJECT / LLM_PASS / LLM_REJECT
    """
    verdict, kw_score = rule_prescreen(title, snippet, city)

    if verdict == "PASS":
        return "PASS", kw_score, "RULE_PASS"
    if verdict == "REJECT":
        return "REJECT", kw_score, "RULE_REJECT"

    # 边际 → LLM
    if use_llm:
        llm_pass, reason = llm_prescreen(title, snippet)
        if llm_pass:
            return "LLM_PASS", kw_score, reason
        return "LLM_REJECT", kw_score, reason

    return "MARGINAL", kw_score, "NO_LLM"


if __name__ == "__main__":
    # 快速测试
    tests = [
        ("某市修订《产业引导基金管理办法》征求意见建议",
         "来源 |某市市委财经办 某市产业引导基金管理办法(征求意见稿) 01总则第一条"),
        ("百度百科_某市",
         "某市是某省省会城市，位于中国某地区"),
        ("政府引导基金如何选GP",
         "2007年,财政部、科技部制定了《科技型中小企业创业投资引导基金管理暂行办法》"),
    ]
    for title, snippet in tests:
        verdict, score, reason = prescreen(title, snippet, use_llm=False)
        print(f"[{verdict}] kw={score} | {title[:50]}")
