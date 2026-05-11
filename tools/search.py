from __future__ import annotations

import json

from tools.web_search import ddg_search_snippets


def web_search(query: str) -> str:
    results = ddg_search_snippets(query, max_results=5)
    if not results:
        return "[]"
    return json.dumps(results, ensure_ascii=False)