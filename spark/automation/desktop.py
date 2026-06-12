"""Desktop Automation — System-level operations."""

from __future__ import annotations

import logging
import subprocess
from typing import Any

logger = logging.getLogger("spark.automation.desktop")


class DesktopAutomation:
    """Automates desktop operations."""

    def open_application(self, app_name: str) -> dict[str, Any]:
        try:
            from tools.system import open_application
            result = open_application(app_name)
            return {"success": True, "app": app_name, "result": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def type_text(self, text: str) -> dict[str, Any]:
        try:
            from tools.system import type_text
            result = type_text(text)
            return {"success": True, "result": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def take_screenshot(self) -> dict[str, Any]:
        try:
            from tools.screen import take_screenshot
            result = take_screenshot()
            return {"success": True, "path": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_clipboard(self) -> str:
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            return ""

    def set_clipboard(self, text: str) -> bool:
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except Exception:
            return False
