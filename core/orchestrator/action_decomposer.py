from __future__ import annotations

import re
from typing import Any


_SEARCH_ENGINE_URLS = {
    "github": "https://github.com/search?q=",
    "google": "https://www.google.com/search?q=",
    "bing": "https://www.bing.com/search?q=",
    "youtube": "https://www.youtube.com/results?search_query=",
    "stackoverflow": "https://stackoverflow.com/search?q=",
    "reddit": "https://www.reddit.com/search/?q=",
}

_ACTION_PATTERN = re.compile(
    r"\b(?:open|launch|start|run|search|find|look up|lookup|research|weather|forecast|temperature|time|date|clock)\b",
    re.IGNORECASE,
)


def _split_phrases(text: str) -> list[str]:
    matches = list(_ACTION_PATTERN.finditer(text or ""))
    if not matches:
        return []

    phrases: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        phrase = text[start:end].strip(" ,.;")
        if phrase:
            phrases.append(phrase)
    return phrases


def _clean_target(text: str) -> str:
    cleaned = re.sub(
        r"\b(?:please|now|for me|for us|in chrome|in browser|on chrome|in another tab|in a new tab|new tab|another tab)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    cleaned = re.sub(r"^\s*(?:the|my|app|application|program)\s+", "", cleaned, flags=re.IGNORECASE)
    return " ".join(cleaned.split()).strip(" .")


def _clean_search_query(text: str) -> str:
    cleaned = re.sub(
        r"\b(?:please|now|for me|for us|in another tab|in a new tab|new tab|another tab)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    return " ".join(cleaned.split()).strip(" .")


def _open_action(target: str) -> dict[str, Any] | None:
    target = _clean_target(target)
    if not target:
        return None

    if re.search(r"\b(map|maps|google maps)\b", target, flags=re.IGNORECASE):
        location = re.sub(r"\b(?:open|launch|start|run|map|maps|google maps|chrome|browser)\b", " ", target, flags=re.IGNORECASE)
        location = " ".join(location.split()).strip() or "current location"
        return {"tool": "open_url", "args": {"query": location}, "label": f"maps:{location}"}

    return {"tool": "open_app", "args": {"app": target}, "label": f"app:{target}"}


def _search_action(query: str) -> dict[str, Any] | None:
    query = _clean_search_query(query)
    if not query:
        return None

    lowered = query.lower()
    for engine, base_url in _SEARCH_ENGINE_URLS.items():
        if engine in lowered:
            terms = lowered.replace(engine, "").strip()
            query_string = re.sub(r"\s+", "+", terms or query)
            return {"tool": "open_url", "args": {"url": base_url + query_string}, "label": f"{engine}:{terms or query}"}

    return {"tool": "web_search", "args": {"query": query}, "label": f"search:{query}"}


def decompose_explicit_actions(text: str) -> list[dict[str, Any]]:
    """Turn a chained command into a list of deterministic tool actions."""
    if not text or not text.strip():
        return []

    phrases = _split_phrases(text)
    if not phrases:
        return []

    actions: list[dict[str, Any]] = []
    for phrase in phrases:
        lowered = phrase.lower().strip()

        if lowered.startswith(("open ", "launch ", "start ", "run ")):
            verb = lowered.split(None, 1)[0]
            raw_tail = phrase[len(verb):].strip()
            targets = [item.strip() for item in re.split(r"\b(?:and|,|&|plus|also)\b", raw_tail, flags=re.IGNORECASE) if item.strip()]
            if len(targets) > 1:
                for target in targets:
                    action = _open_action(target)
                    if action:
                        actions.append(action)
            else:
                action = _open_action(raw_tail)
                if action:
                    actions.append(action)
            continue

        if lowered.startswith(("search ", "find ", "look up ", "lookup ", "research ")):
            action = _search_action(phrase.split(None, 1)[1] if len(phrase.split(None, 1)) > 1 else "")
            if action:
                actions.append(action)
            continue

        if any(word in lowered for word in ["weather", "forecast", "temperature", "rain", "humidity"]):
            location = re.search(r"\b(?:in|for|at)\s+(.+)$", phrase, flags=re.IGNORECASE)
            value = location.group(1) if location and location.group(1) else phrase
            value = re.split(r"\b(?:and then|then|and|also|plus)\b|,", value, maxsplit=1, flags=re.IGNORECASE)[0]
            value = re.sub(r"\b(?:weather|forecast|temperature|what is|what's|is it|like|today|now|currently|the)\b", " ", value, flags=re.IGNORECASE)
            value = re.sub(r"^\s*(?:in|for|at)\s+", "", value, flags=re.IGNORECASE).strip(" .") or "Palakkad"
            actions.append({"tool": "get_weather", "args": {"location": value}, "label": f"weather:{value}"})
            continue

        if any(word in lowered for word in ["time", "date", "clock"]):
            actions.append({"tool": "get_time", "args": {}, "label": "time"})

    return actions