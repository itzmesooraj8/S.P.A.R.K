"""Open URLs, maps, and apps by voice command."""

from __future__ import annotations

import os
import subprocess
import sys
import webbrowser


def open_url(url: str = "", query: str = "") -> str:
    if query and not url:
        map_url = f"https://maps.google.com/?q={query.replace(' ', '+')}"
        webbrowser.open(map_url)
        return f"Opened map for: {query}"
    if url:
        webbrowser.open(url)
        return f"Opened: {url}"
    return "No URL or query provided."


def open_app(app_name: str) -> str:
    """Open an installed application."""
    apps = {
        "spotify": ["spotify"],
        "chrome": ["google-chrome"] if sys.platform == "linux" else ["chrome"],
        "vscode": ["code"],
        "terminal": ["gnome-terminal"] if sys.platform == "linux" else ["cmd"],
    }
    cmd = apps.get(app_name.lower())
    if not cmd:
        return f"Unknown app: {app_name}"

    try:
        if sys.platform == "win32":
            if app_name.lower() == "terminal":
                subprocess.Popen(["cmd", "/c", "start", "", "cmd"], shell=False)
            elif app_name.lower() == "vscode":
                subprocess.Popen(["cmd", "/c", "start", "", "code"], shell=False)
            else:
                subprocess.Popen(["cmd", "/c", "start", "", cmd[0]], shell=False)
        else:
            subprocess.Popen(cmd)
        return f"Opened {app_name}"
    except Exception as exc:
        return f"Unable to open {app_name}: {exc}"