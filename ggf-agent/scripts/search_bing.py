# DEPRECATED — use ggf_agent package instead (from ggf_agent.xxx import ...)
"""
Bing 搜索适配器 — 通过 cn.bing.com HTML 抓取（无需 API key）。

在中国大陆可用，不走 api.bing.microsoft.com。
"""
from __future__ import annotations

import re
import time
from typing import Any
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

BING_URL = "https://cn.bing.com/search"


def search_bing(query: str, count: int = 15, timeout: int = 20) -> list[dict]:
    """
    通过 cn.bing.com 搜索，解析 HTML 结果。

    Args:
        query: 检索式（会自动拼接 site:gov.cn）
        count: 期望返回条数

    Returns:
        [{"title": ..., "url": ..., "snippet": ..., "source": "bing"}, ...]
    """
    full_query = f"{query} site:gov.cn"
    params = {
        "q": full_query,
        "count": min(count, 50),
        "setlang": "zh-CN",
        "cc": "cn",
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        resp = requests.get(BING_URL, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[bing] 请求失败: {query[:40]}... — {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # Bing 搜索结果在 <li class="b_algo"> 中
    for item in soup.select("li.b_algo"):
        link = item.select_one("h2 a")
        snippet_el = item.select_one(".b_caption p, .b_lineclamp2, .b_algoSlug")
        if not link:
            continue

        title = link.get_text(strip=True)
        url = link.get("href", "")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        if title and url:
            results.append({
                "source": "bing",
                "title": title,
                "url": url,
                "snippet": snippet[:200],
            })

    if not results:
        # 备用：尝试新版 Bing 布局 (.b_title h2 a)
        for item in soup.select(".b_title h2 a, h2 a[href]"):
            results.append({
                "source": "bing",
                "title": item.get_text(strip=True),
                "url": item.get("href", ""),
                "snippet": "",
            })

    return results[:count]


if __name__ == "__main__":
    results = search_bing("引导基金 管理办法")
    print(f"命中 {len(results)} 条")
    for r in results[:5]:
        print(f"  {r['title'][:70]}")
        print(f"  {r['url'][:100]}")
        print(f"  {r['snippet'][:100]}")
        print()
