"""Desktop Intelligence — System-level operations."""

from __future__ import annotations

import logging
import subprocess
import os
from typing import Any

logger = logging.getLogger("spark.automation.desktop_intel")


class DesktopIntelligence:
    """
    Intelligent desktop automation with Windows app mapping.

    Maps common app names to their Windows executables.
    """

    APP_MAP = {
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "paint": "mspaint.exe",
        "word": "winword.exe",
        "excel": "excel.exe",
        "powerpoint": "powerpnt.exe",
        "chrome": "chrome.exe",
        "firefox": "firefox.exe",
        "edge": "msedge.exe",
        "brave": "brave.exe",
        "opera": "opera.exe",
        "vs code": "code.exe",
        "visual studio code": "code.exe",
        "cursor": "cursor.exe",
        "terminal": "wt.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "file explorer": "explorer.exe",
        "task manager": "taskmgr.exe",
        "settings": "ms-settings:",
        "microsoft store": "ms-windows-store:",
        "spotify": "spotify.exe",
        "discord": "discord.exe",
        "slack": "slack.exe",
        "teams": "teams.exe",
        "zoom": "zoom.exe",
        "telegram": r"C:\Users\itzme\AppData\Roaming\Telegram Desktop\Telegram.exe",
        "telegram desktop": r"C:\Users\itzme\AppData\Roaming\Telegram Desktop\Telegram.exe",
        "whatsapp": "whatsapp.exe",
        "obsidian": "obsidian.exe",
        "notion": "notion.exe",
        "figma": "figma.exe",
        "photoshop": "photoshop.exe",
        "blender": "blender.exe",
        "vlc": "vlc.exe",
        "mpv": "mpv.exe",
        "7zip": "7z.exe",
        "winrar": "winrar.exe",
    }

    def open_application(self, app_name: str) -> dict[str, Any]:
        """Open an application by name."""
        app_lower = app_name.lower().strip()

        if app_lower in self.APP_MAP:
            exe = self.APP_MAP[app_lower]
            try:
                if exe.endswith(":"):
                    os.startfile(exe)
                    return {"success": True, "app": app_name, "exe": exe}

                if os.path.exists(exe):
                    subprocess.Popen([exe], shell=False)
                    return {"success": True, "app": app_name, "exe": exe}

                subprocess.Popen(f'start {exe}', shell=True)
                return {"success": True, "app": app_name, "exe": exe}
            except Exception as exc:
                return {"success": False, "error": f"Failed to open {app_name}: {exc}"}

        try:
            subprocess.Popen(f'start {app_name}', shell=True)
            return {"success": True, "app": app_name}
        except Exception as exc:
            return {"success": False, "error": f"Could not find or open {app_name}: {exc}"}

    def type_text(self, text: str) -> dict[str, Any]:
        """Type text into focused window."""
        try:
            import pyautogui
            pyautogui.typewrite(text, interval=0.05)
            return {"success": True, "text": text}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def take_screenshot(self) -> dict[str, Any]:
        """Take a screenshot."""
        try:
            import pyautogui
            path = "screenshot.png"
            pyautogui.screenshot(path)
            return {"success": True, "path": path}
        except ImportError:
            return {"success": False, "error": "pyautogui not installed"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def get_clipboard(self) -> str:
        """Get clipboard content."""
        try:
            import pyperclip
            return pyperclip.paste()
        except Exception:
            return ""

    def set_clipboard(self, text: str) -> bool:
        """Set clipboard content."""
        try:
            import pyperclip
            pyperclip.copy(text)
            return True
        except Exception:
            return False
