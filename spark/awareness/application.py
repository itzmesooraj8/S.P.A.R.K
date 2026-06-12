"""Application Awareness — Tracks running applications."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.awareness.application")


class ApplicationAwareness:
    """Tracks and monitors application state."""

    def __init__(self) -> None:
        self._active_apps: list[str] = []
        self._focused_app: str = ""
        self._last_scan: float = 0.0

    def scan(self) -> dict[str, Any]:
        apps = self._get_running_apps()
        focused = self._get_focused_app()
        self._active_apps = apps
        self._focused_app = focused
        self._last_scan = time.time()
        return {
            "active": apps,
            "focused": focused,
            "count": len(apps),
            "timestamp": self._last_scan,
        }

    def _get_running_apps(self) -> list[str]:
        try:
            import psutil
            return [p.name() for p in psutil.process_iter(["name"]) if p.info.get("name")]
        except Exception:
            return []

    def _get_focused_app(self) -> str:
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            return win.title if win else "Unknown"
        except Exception:
            return "Unknown"

    def is_app_running(self, app_name: str) -> bool:
        return app_name.lower() in [a.lower() for a in self._active_apps]

    def get_context(self) -> dict[str, Any]:
        return {
            "focused": self._focused_app,
            "active_count": len(self._active_apps),
            "apps": self._active_apps[:10],
        }
