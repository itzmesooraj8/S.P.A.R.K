"""Desktop Intelligence — Not just open_app() but intelligent interaction."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.automation.desktop_intel")


class DesktopIntelligence:
    """
    Intelligent desktop automation.

    Not just:
        open_app()

    But:
        Locate button → Understand window → Click intelligently
    """

    def __init__(self) -> None:
        self._last_action = ""

    def find_element(self, description: str, screenshot_path: str | None = None) -> dict[str, Any]:
        """Find a UI element by description using vision."""
        try:
            from spark.vision.understand import VisionUnderstander
            vision = VisionUnderstander()
            if screenshot_path:
                result = vision.understand(screenshot_path, f"Find the '{description}' element. Return its approximate position.")
                return {"found": True, "details": result.get("analysis", ""), "position": None}
        except Exception:
            pass
        return {"found": False, "error": "Vision not available"}

    def click_element(self, x: int, y: int) -> dict[str, Any]:
        """Click at coordinates."""
        try:
            import pyautogui
            pyautogui.click(x, y)
            return {"success": True, "x": x, "y": y}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def type_text(self, text: str, interval: float = 0.05) -> dict[str, Any]:
        """Type text with human-like delay."""
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=interval)
            return {"success": True, "text": text}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def hotkey(self, *keys: str) -> dict[str, Any]:
        """Press a hotkey combination."""
        try:
            import pyautogui
            pyautogui.hotkey(*keys)
            return {"success": True, "keys": list(keys)}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_screen_size(self) -> tuple[int, int]:
        try:
            import pyautogui
            return pyautogui.size()
        except Exception:
            return (1920, 1080)

    def get_mouse_position(self) -> tuple[int, int]:
        try:
            import pyautogui
            return pyautogui.position()
        except Exception:
            return (0, 0)

    def move_mouse(self, x: int, y: int, duration: float = 0.3) -> dict[str, Any]:
        try:
            import pyautogui
            pyautogui.moveTo(x, y, duration=duration)
            return {"success": True, "x": x, "y": y}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def scroll(self, clicks: int) -> dict[str, Any]:
        try:
            import pyautogui
            pyautogui.scroll(clicks)
            return {"success": True, "clicks": clicks}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
