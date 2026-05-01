"""
S.P.A.R.K. Web Intelligence Tool
Provides real-time web search using DuckDuckGo (no API key required)
and a lightweight scraper for structured data like stocks and news.
"""

import logging
import re
import urllib.parse
import urllib.request
import json
import html

logger = logging.getLogger("SPARK_WEB")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _fetch(url: str, timeout: int = 6) -> str:
    """Raw HTTP fetch, returns text or empty string on failure."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        logger.warning(f"Fetch failed for {url}: {e}")
        return ""


def ddg_instant_answer(query: str) -> str:
    """
    DuckDuckGo Instant Answer API — zero-click facts.
    Returns a short plain-text answer or empty string.
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://api.duckduckgo.com/?q={encoded}&format=json&no_redirect=1&no_html=1&skip_disambig=1"
    raw = _fetch(url)
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        if data.get("AbstractText"):
            return data["AbstractText"]
        if data.get("Answer"):
            return data["Answer"]
        topics = data.get("RelatedTopics", [])
        if topics and isinstance(topics[0], dict) and topics[0].get("Text"):
            return topics[0]["Text"]
    except Exception:
        pass
    return ""


def ddg_search_snippets(query: str, max_results: int = 3) -> list[dict]:
    """
    DuckDuckGo HTML search — scrapes snippet + URL from results page.
    Returns list of {title, snippet, url}.
    """
    encoded = urllib.parse.quote_plus(query)
    url = f"https://html.duckduckgo.com/html/?q={encoded}"
    html_resp = _fetch(url)
    if not html_resp:
        return []

    results = []
    blocks = re.findall(
        r'class="result__title".*?href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</span>',
        html_resp, re.DOTALL
    )
    for href, title_raw, snippet_raw in blocks[:max_results]:
        title = html.unescape(re.sub(r"<[^>]+>", "", title_raw).strip())
        snippet = html.unescape(re.sub(r"<[^>]+>", "", snippet_raw).strip())
        real_url = href
        if "uddg=" in href:
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                real_url = urllib.parse.unquote(m.group(1))
        results.append({"title": title, "snippet": snippet, "url": real_url})
    return results


def get_stock_summary(symbol_or_name: str) -> str:
    """
    Fetches stock price summary from Yahoo Finance Quote API.
    """
    query = symbol_or_name.strip()

    INDIAN_INDEXES = {
        "nifty": "^NSEI",
        "nifty 50": "^NSEI",
        "nifty50": "^NSEI",
        "sensex": "^BSESN",
        "bse": "^BSESN",
        "nse": "^NSEI",
        "bank nifty": "^NSEBANK",
    }
    lower = query.lower()
    for key, sym in INDIAN_INDEXES.items():
        if key in lower:
            query = sym
            break

    if not re.match(r"[\^.]", query) and len(query.split()) == 1:
        query = query.upper() + ".NS"

    encoded = urllib.parse.quote(query)
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={encoded}"
    raw = _fetch(url)
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        result = data["quoteResponse"]["result"]
        if not result:
            return ""
        
        meta = result[0]
        price = meta.get("regularMarketPrice", 0)
        change = meta.get("regularMarketChange", 0)
        pct = meta.get("regularMarketChangePercent", 0)
        currency = meta.get("currency", "INR")
        symbol = meta.get("symbol", query)
        name = meta.get("longName") or meta.get("shortName") or symbol
        
        direction = "up" if change >= 0 else "down"
        arrow = "▲" if change >= 0 else "▼"
        return (
            f"{name} is trading at {currency} {price:,.2f}, "
            f"{arrow} {abs(change):,.2f} ({abs(pct):.2f}%) {direction}."
        )
    except Exception as e:
        logger.warning(f"Stock parse error: {e}")
        return ""


def get_indian_market_summary() -> str:
    """Returns a spoken summary of Nifty 50 and Sensex."""
    results = []
    for name, symbol in [("Nifty 50", "^NSEI"), ("Sensex", "^BSESN")]:
        s = get_stock_summary(symbol)
        if s:
            results.append(s)
    if results:
        return " ".join(results)
    return ""


def web_search_answer(query: str) -> str:
    """Master entry point for queries."""
    q_lower = query.lower()

    # Route stock / market queries
    stock_keywords = ["stock", "share price", "nifty", "sensex", "market", "bse", "nse", "trading", "index"]
    
    # Bug 3 Fix: If user asks for "top" or "best", do a web search instead of market summary
    is_top_query = any(k in q_lower for k in ["top", "best", "performing", "gainers", "losers", "recommendation"])
    
    if any(k in q_lower for k in stock_keywords) and not is_top_query:
        if any(k in q_lower for k in ["indian market", "indian stock", "nifty", "sensex", "bse", "nse"]):
            summary = get_indian_market_summary()
            if summary:
                return summary
        
        clean = re.sub(
            r"\b(stock|share|price|of|the|tell|me|about|today|yesterday|current|details)\b",
            "", q_lower, flags=re.IGNORECASE
        ).strip()
        if clean:
            s = get_stock_summary(clean)
            if s:
                return s

    instant = ddg_instant_answer(query)
    if instant and len(instant) > 20:
        return instant[:300].rstrip() + ("..." if len(instant) > 300 else "")

    snippets = ddg_search_snippets(query, max_results=2)
    if snippets:
        parts = [r["snippet"] for r in snippets if r["snippet"]]
        combined = " ".join(parts)
        return combined[:350].rstrip() + ("..." if len(combined) > 350 else "")

    return ""
