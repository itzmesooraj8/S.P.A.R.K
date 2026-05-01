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
        # AbstractText is the Wikipedia-style summary
        if data.get("AbstractText"):
            return data["AbstractText"]
        # Answer is the instant calculator / unit converter result
        if data.get("Answer"):
            return data["Answer"]
        # RelatedTopics first item
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
    html = _fetch(url)
    if not html:
        return []

    results = []
    # Extract result blocks
    blocks = re.findall(
        r'class="result__title".*?href="([^"]+)"[^>]*>(.*?)</a>.*?class="result__snippet"[^>]*>(.*?)</span>',
        html, re.DOTALL
    )
    for href, title_raw, snippet_raw in blocks[:max_results]:
        title = re.sub(r"<[^>]+>", "", title_raw).strip()
        snippet = re.sub(r"<[^>]+>", "", snippet_raw).strip()
        # DDG wraps URLs — extract the real one
        real_url = href
        if "uddg=" in href:
            m = re.search(r"uddg=([^&]+)", href)
            if m:
                real_url = urllib.parse.unquote(m.group(1))
        results.append({"title": title, "snippet": snippet, "url": real_url})
    return results


def get_stock_summary(symbol_or_name: str) -> str:
    """
    Fetches stock price summary from Yahoo Finance.
    Works for NSE stocks (append .NS), BSE (.BO), or US tickers.
    Auto-detects Indian market if name contains common Indian terms.
    """
    query = symbol_or_name.strip()

    # Heuristic: if user said "Nifty", "Sensex", "NSE", map to index symbols
    INDIAN_INDEXES = {
        "nifty": "^NSEI",
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

    # If it looks like a plain company name (no dots, no ^), add .NS for NSE
    if not re.match(r"[\^.]", query) and len(query.split()) == 1:
        # Try NSE first
        query = query.upper() + ".NS"

    encoded = urllib.parse.quote(query)
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{encoded}?interval=1d&range=2d"
    raw = _fetch(url)
    if not raw:
        return ""
    try:
        data = json.loads(raw)
        meta = data["chart"]["result"][0]["meta"]
        price = meta.get("regularMarketPrice", 0)
        prev = meta.get("chartPreviousClose", 0)
        change = price - prev
        pct = (change / prev * 100) if prev else 0
        currency = meta.get("currency", "INR")
        symbol = meta.get("symbol", query)
        name = meta.get("longName") or meta.get("shortName") or symbol
        direction = "up" if change >= 0 else "down"
        arrow = "▲" if change >= 0 else "▼"
        return (
            f"{name} is trading at {currency} {price:,.2f}, "
            f"{arrow} {abs(change):,.2f} ({abs(pct):.2f}%) {direction} from yesterday."
        )
    except Exception as e:
        logger.warning(f"Stock parse error: {e}")
        return ""


def get_indian_market_summary() -> str:
    """
    Returns a spoken summary of Nifty 50 and Sensex — the two main Indian indexes.
    """
    results = []
    for name, symbol in [("Nifty 50", "^NSEI"), ("Sensex", "^BSESN")]:
        s = get_stock_summary(symbol)
        if s:
            results.append(s)
    if results:
        return " ".join(results)
    return ""


def web_search_answer(query: str) -> str:
    """
    Master entry point. Returns the best spoken answer for a given query.
    Priority: instant answer → stock data → snippet summary.
    """
    q_lower = query.lower()

    # Route stock / market queries
    stock_keywords = ["stock", "share price", "nifty", "sensex", "market", "bse", "nse",
                      "trading", "index", "equity", "ipo"]
    if any(k in q_lower for k in stock_keywords):
        # Check for "Indian market" broad query
        if any(k in q_lower for k in ["indian market", "indian stock", "nifty", "sensex", "bse", "nse"]):
            summary = get_indian_market_summary()
            if summary:
                return summary
        # Single stock query — try to extract ticker/company name
        # Remove noise words
        clean = re.sub(
            r"\b(stock|share|price|of|the|tell|me|about|today|yesterday|current|details)\b",
            "", q_lower, flags=re.IGNORECASE
        ).strip()
        if clean:
            s = get_stock_summary(clean)
            if s:
                return s

    # Try DuckDuckGo instant answer first (fast)
    instant = ddg_instant_answer(query)
    if instant and len(instant) > 20:
        # Truncate to ~300 chars for TTS
        return instant[:300].rstrip() + ("..." if len(instant) > 300 else "")

    # Fall back to snippet search
    snippets = ddg_search_snippets(query, max_results=2)
    if snippets:
        parts = []
        for r in snippets:
            if r["snippet"]:
                parts.append(r["snippet"])
        combined = " ".join(parts)
        return combined[:350].rstrip() + ("..." if len(combined) > 350 else "")

    return ""
