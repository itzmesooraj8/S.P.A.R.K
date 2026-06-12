"""Playwright Browser Intelligence — Not just open_url() but intelligent interaction."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("spark.automation.playwright")


class PlaywrightBrowser:
    """
    Intelligent browser automation using Playwright.

    Not just:
        open_url()

    But:
        Find login button → Click login → Fill form → Extract data
    """

    def __init__(self) -> None:
        self._browser = None
        self._page = None
        self._context = None

    async def launch(self, headless: bool = True) -> bool:
        try:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=headless)
            self._context = await self._browser.new_context()
            self._page = await self._context.new_page()
            logger.info("Playwright browser launched")
            return True
        except ImportError:
            logger.error("Playwright not installed: pip install playwright && playwright install")
            return False
        except Exception as exc:
            logger.error("Playwright launch failed: %s", exc)
            return False

    async def navigate(self, url: str) -> dict[str, Any]:
        if not self._page:
            return {"success": False, "error": "Browser not launched"}
        try:
            await self._page.goto(url)
            title = await self._page.title()
            return {"success": True, "url": url, "title": title}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def click(self, selector: str) -> dict[str, Any]:
        if not self._page:
            return {"success": False, "error": "Browser not launched"}
        try:
            await self._page.click(selector)
            return {"success": True, "selector": selector}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def fill(self, selector: str, text: str) -> dict[str, Any]:
        if not self._page:
            return {"success": False, "error": "Browser not launched"}
        try:
            await self._page.fill(selector, text)
            return {"success": True, "selector": selector, "text": text}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def extract_text(self, selector: str = "body") -> dict[str, Any]:
        if not self._page:
            return {"success": False, "error": "Browser not launched"}
        try:
            text = await self._page.inner_text(selector)
            return {"success": True, "text": text}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def extract_data(self, selectors: dict[str, str]) -> dict[str, Any]:
        if not self._page:
            return {"success": False, "error": "Browser not launched"}
        results = {}
        for key, selector in selectors.items():
            try:
                element = await self._page.query_selector(selector)
                if element:
                    results[key] = await element.inner_text()
            except Exception:
                results[key] = None
        return {"success": True, "data": results}

    async def screenshot(self, path: str = "screenshot.png") -> dict[str, Any]:
        if not self._page:
            return {"success": False, "error": "Browser not launched"}
        try:
            await self._page.screenshot(path=path)
            return {"success": True, "path": path}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def wait_for(self, selector: str, timeout: int = 10000) -> dict[str, Any]:
        if not self._page:
            return {"success": False, "error": "Browser not launched"}
        try:
            await self._page.wait_for_selector(selector, timeout=timeout)
            return {"success": True, "selector": selector}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def evaluate(self, script: str) -> dict[str, Any]:
        if not self._page:
            return {"success": False, "error": "Browser not launched"}
        try:
            result = await self._page.evaluate(script)
            return {"success": True, "result": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    async def close(self) -> None:
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
        self._browser = None
        self._page = None

    def info(self) -> dict[str, Any]:
        return {"browser": "playwright", "launched": self._browser is not None}
