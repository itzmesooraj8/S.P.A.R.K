"""Screen Awareness — Can observe what's on screen."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.awareness.screen")


class ScreenAwareness:
    """Observes screen content and changes."""

    def __init__(self) -> None:
        self._last_screenshot: str | None = None
        self._last_analysis: dict[str, Any] = {}

    def observe(self, screenshot_path: str | None = None) -> dict[str, Any]:
        result = {
            "timestamp": time.time(),
            "screenshot": screenshot_path,
            "changed": False,
            "analysis": {},
        }
        if screenshot_path and screenshot_path != self._last_screenshot:
            result["changed"] = True
            self._last_screenshot = screenshot_path
        return result

    def get_active_window(self) -> str:
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            return win.title if win else "Unknown"
        except Exception:
            return "Unknown"

    def get_screen_text(self, screenshot_path: str) -> str:
        try:
            from core.vision import describe_screen
            return describe_screen(screenshot_path, "Read all visible text on screen")
        except Exception:
            return ""

    def detect_changes(self, path1: str, path2: str) -> bool:
        return path1 != path2
