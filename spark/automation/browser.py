"""Browser Automation — Web browsing and interaction."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("spark.automation.browser")


class BrowserAutomation:
    """Automates browser operations."""

    def __init__(self) -> None:
        self._browser = None

    async def open_url(self, url: str) -> dict[str, Any]:
        try:
            import webbrowser
            webbrowser.open(url)
            return {"success": True, "url": url}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def search(self, query: str) -> dict[str, Any]:
        """Search using LLM knowledge for reliable results."""
        try:
            from spark.llm_bridge import LLMBridge
            import httpx

            bridge = LLMBridge()
            if bridge.budget.can_use_groq():
                try:
                    import os
                    api_key = os.environ.get("GROQ_API_KEY", "")
                    if api_key:
                        model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")
                        prompt = f"Provide a concise summary about: {query}. Include 3-5 key points or recent developments if applicable. Be factual and specific."
                        response = httpx.post(
                            "https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                            json={"model": model, "messages": [{"role": "user", "content": prompt}], "max_tokens": 300},
                            timeout=30.0,
                        )
                        if response.status_code == 200:
                            result = response.json()["choices"][0]["message"]["content"]
                            bridge.budget.record_usage(response.json().get("usage", {}).get("total_tokens", 0), "groq")
                            return {"success": True, "query": query, "result": result}
                except Exception:
                    pass

            return {"success": False, "error": "Search unavailable"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _parse_search_results(self, html: str) -> str:
        """Parse search results from HTML."""
        import re
        results = []
        snippets = re.findall(r'class="result__snippet">(.*?)</a>', html, re.DOTALL)
        for snippet in snippets[:5]:
            clean = re.sub(r'<[^>]+>', '', snippet).strip()
            if clean:
                results.append(clean)
        if results:
            return "\n\n".join(results)
        return "No search results found"

    async def screenshot(self) -> dict[str, Any]:
        try:
            import pyautogui
            path = "screenshot.png"
            pyautogui.screenshot(path)
            return {"success": True, "path": path}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
