"""Open URLs, maps, and desktop apps."""

from __future__ import annotations

import subprocess
import sys
import webbrowser
import time
import psutil
import shutil


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
    """
    Open any application on Windows/Linux/Mac by name.
    Uses dynamic system search instead of a hardcoded list.
    """
    import subprocess, sys, shutil

    app = app_name.strip().lower()

    # Windows: use the Start menu search via explorer shell and verify a process started
    if sys.platform == "win32":
        before = {p.info.get("name", "").lower() for p in psutil.process_iter(["name"]) if p.info.get("name")}

        # Method 1: Try direct executable name
        if shutil.which(app):
            try:
                subprocess.Popen([app])
            except Exception:
                pass
            time.sleep(0.6)
            after = {p.info.get("name", "").lower() for p in psutil.process_iter(["name"]) if p.info.get("name")}
            new = sorted(name for name in after - before if name)
            if new:
                return f"SUCCESS: Launched. New process: {new[0]}"
            return f"LAUNCH_FAILED: Tried to run {app_name} but no new process detected."

        # Method 2: Try common Windows app names
        win_aliases = {
            "camera": "microsoft.windows.camera:",
            "file manager": "explorer.exe",
            "file explorer": "explorer.exe",
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "paint": "mspaint.exe",
            "task manager": "taskmgr.exe",
            "settings": "ms-settings:",
            "store": "ms-windows-store:",
            "mail": "outlookmail:",
            "calendar": "outlookcal:",
            "photos": "ms-photos:",
            "maps": "bingmaps:",
            "music": "mswindowsmusic:",
        }
        if app in win_aliases:
            target = win_aliases[app]
            try:
                if target.endswith(".exe"):
                    subprocess.Popen([target])
                else:
                    subprocess.Popen(["explorer.exe", target])
            except Exception:
                pass
            time.sleep(0.6)
            after = {p.info.get("name", "").lower() for p in psutil.process_iter(["name"]) if p.info.get("name")}
            new = sorted(name for name in after - before if name)
            if new:
                return f"SUCCESS: Launched. New process: {new[0]}"
            return f"LAUNCH_FAILED: Tried to open {app_name} but no new process detected."

        # Method 3: Try as a URI scheme (works for Spotify, Telegram, etc.)
        uri_schemes = {
            "spotify": "spotify:",
            "telegram": "tg:",
            "discord": "discord:",
            "slack": "slack:",
            "zoom": "zoommtg:",
            "teams": "msteams:",
            "whatsapp": "whatsapp:",
            "vlc": "vlc:",
        }
        if app in uri_schemes:
            try:
                subprocess.Popen(["explorer.exe", uri_schemes[app]])
            except Exception:
                pass
            time.sleep(0.6)
            after = {p.info.get("name", "").lower() for p in psutil.process_iter(["name"]) if p.info.get("name")}
            new = sorted(name for name in after - before if name)
            if new:
                return f"SUCCESS: Launched. New process: {new[0]}"
            return f"LAUNCH_FAILED: Tried URI scheme for {app_name} but no new process detected."

        # Method 4: Search Windows Start menu via PowerShell (best-effort)
        try:
            ps_cmd = (
                f"$app = Get-StartApps | Where-Object {{$_.Name -like '*{app_name}*'}} | "
                f"Select-Object -First 1; "
                f"if ($app) {{ Start-Process shell:appsFolder\\$($app.AppID) }}"
            )
            try:
                subprocess.Popen(
                    ["powershell", "-WindowStyle", "Hidden", "-Command", ps_cmd],
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            except Exception:
                pass
            time.sleep(0.8)
            after = {p.info.get("name", "").lower() for p in psutil.process_iter(["name"]) if p.info.get("name")}
            new = sorted(name for name in after - before if name)
            if new:
                return f"SUCCESS: Launched. New process: {new[0]}"
            return f"LAUNCH_FAILED: Searched Start menu for {app_name} but no new process detected."
        except Exception as e:
            return f"Could not open {app_name}: {e}"

    # Linux
    elif sys.platform.startswith("linux"):
        linux_aliases = {
            "file manager": ["nautilus", "thunar", "nemo", "dolphin"],
            "camera": ["cheese", "guvcview"],
            "terminal": ["gnome-terminal", "xterm", "konsole"],
        }
        candidates = linux_aliases.get(app, [app])
        for cmd in candidates:
            if shutil.which(cmd):
                subprocess.Popen([cmd])
                return f"Opened {app_name}."
        return f"Could not find {app_name} on this system."

    # macOS
    else:
        try:
            subprocess.Popen(["open", "-a", app_name])
            return f"Opened {app_name}."
        except Exception as e:
            return f"Could not open {app_name}: {e}"