"""Real news via DuckDuckGo news search."""

from __future__ import annotations

try:
    from duckduckgo_search import DDGS
except Exception:  # pragma: no cover - optional dependency
    DDGS = None


def get_news(topic: str = "technology", max_results: int = 5) -> list[dict]:
    """Return a list of recent news items for a topic."""
    try:
        if DDGS is None:
            return [{"title": "Error", "body": "duckduckgo_search is not installed", "url": ""}]

        with DDGS() as ddgs:
            results = list(ddgs.news(topic, max_results=max_results))

        items = [
            {
                "title": result.get("title", ""),
                "body": result.get("body", ""),
                "url": result.get("url") or result.get("href", ""),
            }
            for result in results
        ]
        return items[:max_results] or [{"title": "No results", "body": f"No news found for {topic}", "url": ""}]
    except Exception as exc:
        return [{"title": "Error", "body": str(exc), "url": ""}]