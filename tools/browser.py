"""Open URLs, maps, and desktop apps."""

from __future__ import annotations

import subprocess
import sys
import webbrowser


def open_url(url: str = "", query: str = "") -> str:
    """Open a URL directly or a Google Maps search for a query."""
    if query and not url:
        map_url = f"https://maps.google.com/?q={query.replace(' ', '+')}"
        webbrowser.open(map_url)
        return f"Opened Google Maps for: {query}"
    if url:
        webbrowser.open(url)
        return f"Opened: {url}"
    return "No URL or query provided."


def open_app(app_name: str) -> str:
    try:
        app = app_name.lower().strip()
        commands = {
            "spotify": {
                "win32": ["cmd", "/c", "start", "", "spotify"],
                "linux": ["spotify"],
                "darwin": ["open", "-a", "Spotify"],
            },
            "chrome": {
                "win32": ["cmd", "/c", "start", "", "chrome"],
                "linux": ["google-chrome"],
                "darwin": ["open", "-a", "Google Chrome"],
            },
            "vscode": {
                "win32": ["cmd", "/c", "start", "", "code"],
                "linux": ["code"],
                "darwin": ["open", "-a", "Visual Studio Code"],
            },
            "terminal": {
                "win32": ["cmd", "/c", "start", "", "cmd"],
                "linux": ["gnome-terminal"],
                "darwin": ["open", "-a", "Terminal"],
            },
        }
        command_map = commands.get(app)
        if not command_map:
            return f"Unknown app: {app_name}"

        platform_key = "win32" if sys.platform.startswith("win") else "darwin" if sys.platform == "darwin" else "linux"
        command = command_map.get(platform_key) or command_map.get("linux") or command_map.get("win32")
        if not command:
            return f"Unknown app: {app_name}"

        subprocess.Popen(command)
        return f"{app} opened"
    except Exception as exc:
        return f"Unable to open {app_name}: {exc}"