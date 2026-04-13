from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

import httpx
from bs4 import BeautifulSoup

from security.policy import RiskLevel, ToolDefinition
from tools.sandbox import emit_telemetry


_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}


def _resolve_ddg_href(href: str) -> str:
    value = (href or "").strip()
    if not value:
        return ""
    if value.startswith("//"):
        value = f"https:{value}"

    parsed_absolute = urlparse(value)
    if parsed_absolute.netloc.endswith("duckduckgo.com") and parsed_absolute.path.startswith("/l/"):
        params = parse_qs(parsed_absolute.query)
        uddg = (params.get("uddg") or [""])[0]
        if uddg:
            return unquote(uddg)

    if value.startswith("/l/?"):
        parsed = urlparse(value)
        params = parse_qs(parsed.query)
        uddg = (params.get("uddg") or [""])[0]
        if uddg:
            return unquote(uddg)
    return value


async def _duckduckgo_search(query: str, max_results: int) -> List[Dict[str, str]]:
    safe_query = quote_plus(query.strip())
    url = f"https://html.duckduckgo.com/html/?q={safe_query}"

    timeout = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        response = await client.get(url, headers=_HEADERS)
        response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")
    cards = soup.select(".result") or soup.select("div.web-result")

    results: List[Dict[str, str]] = []
    for card in cards:
        title_tag = card.select_one("a.result__a") or card.select_one(".result__title a") or card.select_one("a")
        snippet_tag = card.select_one(".result__snippet")
        if not title_tag:
            continue

        title = title_tag.get_text(" ", strip=True)
        href = _resolve_ddg_href(str(title_tag.get("href") or ""))
        snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""

        parsed_href = urlparse(href)
        if parsed_href.netloc.endswith("duckduckgo.com") and parsed_href.path.startswith("/y.js"):
            continue

        if not title or not href:
            continue

        results.append(
            {
                "title": title,
                "url": href,
                "snippet": snippet,
            }
        )
        if len(results) >= max_results:
            break

    return results


async def web_search(args: Dict[str, Any]) -> str:
    """Search the web via DuckDuckGo HTML and return concise ranked results."""
    query = (args or {}).get("query", "").strip()
    if not query:
        return "[ERROR] Missing 'query' argument."

    try:
        max_results = int((args or {}).get("max_results", 5))
    except Exception:
        max_results = 5
    max_results = max(1, min(max_results, 10))

    try:
        results = await _duckduckgo_search(query, max_results)
    except Exception as exc:
        return f"[ERROR] Web search failed: {exc}"

    if not results:
        return f"No results found for '{query}'."

    lines = [f"Web results for: {query}"]
    for idx, item in enumerate(results, start=1):
        lines.append(f"{idx}. {item['title']}")
        lines.append(f"   URL: {item['url']}")
        if item.get("snippet"):
            lines.append(f"   Snippet: {item['snippet']}")

    emit_telemetry(f"web:search {query[:24]}", f"{len(results)} results")
    return "\n".join(lines)


async def web_fetch_url(args: Dict[str, Any]) -> str:
    """Fetch a URL and return cleaned text content for downstream reasoning."""
    url = (args or {}).get("url", "").strip()
    if not url:
        return "[ERROR] Missing 'url' argument."
    if not (url.startswith("http://") or url.startswith("https://")):
        return "[ERROR] URL must start with http:// or https://"

    try:
        max_chars = int((args or {}).get("max_chars", 5000))
    except Exception:
        max_chars = 5000
    max_chars = max(500, min(max_chars, 20000))

    timeout = httpx.Timeout(connect=5.0, read=20.0, write=10.0, pool=5.0)
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=_HEADERS)
            response.raise_for_status()
    except Exception as exc:
        return f"[ERROR] URL fetch failed: {exc}"

    soup = BeautifulSoup(response.text, "lxml")
    title = (soup.title.get_text(" ", strip=True) if soup.title else "Untitled")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    body = soup.get_text(" ", strip=True)
    cleaned = " ".join(body.split())
    excerpt = cleaned[:max_chars]

    emit_telemetry(f"web:fetch {url[:32]}", f"{len(excerpt)} chars")
    return f"Title: {title}\nURL: {url}\n\n{excerpt}"


web_search_tools = [
    ToolDefinition(
        name="web_search",
        handler=web_search,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"],
    ),
    ToolDefinition(
        name="web_fetch_url",
        handler=web_fetch_url,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"],
    ),
]
