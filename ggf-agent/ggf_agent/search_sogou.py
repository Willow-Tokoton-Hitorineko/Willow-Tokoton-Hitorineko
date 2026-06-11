"""
搜狗微信搜索适配器 — 微信公众号文章检索。

微信公众号是政府引导基金信息披露的重要渠道，尤其对区县级政策。
无需 API key，通过 weixin.sogou.com HTML 抓取。
"""
from __future__ import annotations

import re
import time
from urllib.parse import quote, urljoin

import requests
from bs4 import BeautifulSoup

SOGOU_WEIXIN = "https://weixin.sogou.com/weixin"


def search_sogou_weixin(query: str, count: int = 10, timeout: int = 20) -> list[dict]:
    """
    搜狗微信搜索。

    Args:
        query: 检索关键词
        count: 期望返回条数

    Returns:
        [{"title": ..., "url": ..., "snippet": ..., "source": "sogou_weixin"}, ...]
    """
    params = {
        "type": "2",  # 文章搜索
        "query": query,
        "ie": "utf8",
    }
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Accept": "text/html,application/xhtml+xml",
        "Referer": "https://weixin.sogou.com/",
    }

    try:
        resp = requests.get(SOGOU_WEIXIN, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except Exception as exc:
        print(f"[sogou] 请求失败: {query[:40]}... — {exc}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # 搜狗微信结果在 <li class="news-item"> 或 <ul class="news-list2"> 中
    for item in soup.select("li.news-item, li.news-item2, .news-list li"):
        link = item.select_one("h3 a, .txt-box h3 a, a[href*='mp.weixin.qq.com']")
        if not link:
            # 一些布局中链接在标题区域
            link = item.select_one("a")
            if not link or "mp.weixin.qq.com" not in link.get("href", ""):
                continue

        title = link.get_text(strip=True)
        url = urljoin("https://weixin.sogou.com", link.get("href", ""))

        snippet_el = item.select_one(".txt-info, .s-p, p.txt-info, .s-p3")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        if title and url:
            results.append({
                "source": "sogou_weixin",
                "title": title,
                "url": url,
                "snippet": snippet[:200],
            })

    return results[:count]


def resolve_real_url(sogou_url: str, timeout: int = 12) -> str:
    """
    跟随搜狗跳转链接，获取微信公众号文章的真实永久 URL。
    搜狗链接 (weixin.sogou.com/link?url=...) 含过期 token，
    解析后得到 mp.weixin.qq.com 永久链接。
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
        ),
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Referer": "https://weixin.sogou.com/",
    }
    try:
        resp = requests.get(sogou_url, headers=headers, allow_redirects=True,
                          timeout=timeout, stream=True)
        # 只读 headers，不下载正文
        resp.close()
        final = resp.url
        if "mp.weixin.qq.com" in final:
            return final
        # 有时搜狗会用 JS 重定向，尝试从 Location header 获取
        for h in resp.history:
            if "mp.weixin.qq.com" in h.headers.get("Location", ""):
                return h.headers["Location"]
    except Exception:
        pass
    return sogou_url  # 解析失败则返回原链接


def filter_relevant(results: list[dict], city: str = "") -> list[dict]:
    """过滤出包含实质制度内容的微信公众号文章。"""
    inst_keywords = [
        "管理办法", "实施细则", "暂行办法", "实施意见",
        "引导基金", "投资基金", "产业基金", "母基金",
        "设立方案", "遴选", "容错", "返投", "出资",
    ]
    filtered = []
    for r in results:
        text = r["title"] + " " + r["snippet"]
        score = sum(1 for kw in inst_keywords if kw in text)
        if score >= 1:  # 至少命中 1 个制度关键词
            filtered.append(r)
    return filtered


if __name__ == "__main__":
    results = search_sogou_weixin("引导基金 管理办法")
    print(f"命中 {len(results)} 条")
    filtered = filter_relevant(results, "")
    print(f"制度相关: {len(filtered)} 条")
    for r in filtered[:5]:
        print(f"  {r['title'][:70]}")
        print(f"  {r['url'][:100]}")
        print()
