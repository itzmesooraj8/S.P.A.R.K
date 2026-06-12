"""Context Awareness — Maintains situational awareness."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.awareness.context")


class ContextAwareness:
    """Builds and maintains situational context."""

    def __init__(self) -> None:
        self._context: dict[str, Any] = {
            "active_window": "",
            "clipboard": "",
            "time_of_day": "",
            "user_busy": False,
            "recent_activity": [],
        }
        self._last_update: float = 0.0

    def update(self) -> dict[str, Any]:
        self._context["active_window"] = self._get_active_window()
        self._context["clipboard"] = self._get_clipboard()
        self._context["time_of_day"] = self._get_time_period()
        self._last_update = time.time()
        return dict(self._context)

    def _get_active_window(self) -> str:
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            return win.title if win else "Unknown"
        except Exception:
            return "Unknown"

    def _get_clipboard(self) -> str:
        try:
            import pyperclip
            clip = pyperclip.paste()
            return clip[:100] + "..." if len(clip) > 100 else clip
        except Exception:
            return ""

    def _get_time_period(self) -> str:
        import datetime
        hour = datetime.datetime.now().hour
        if 5 <= hour < 12:
            return "morning"
        elif 12 <= hour < 17:
            return "afternoon"
        elif 17 <= hour < 21:
            return "evening"
        return "night"

    def get(self, key: str) -> Any:
        return self._context.get(key)

    def set(self, key: str, value: Any) -> None:
        self._context[key] = value

    def snapshot(self) -> dict[str, Any]:
        return dict(self._context)
