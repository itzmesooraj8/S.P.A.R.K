"""
SPARK Desktop Action Tools
──────────────────────────────────────────────────────────────────────────────
Enables SPARK to interact with the host OS: open applications, URLs, or run
shell commands. Commands that modify system state are AMBER-risk and require
confirmation before execution.
"""
import asyncio
import subprocess
import sys
import os
import webbrowser
import shutil
from typing import Any, Dict

from security.policy import ToolDefinition, RiskLevel, RequiresConfirmationError

# Alias for readability in this module (AMBER risk = requires confirmation)
_AMBER = RiskLevel.YELLOW

# ── App name → executable mapping (Windows-first) ─────────────────────────

_APP_ALIASES: Dict[str, str] = {
    # Browsers
    "chrome":        "chrome",
    "google chrome": "chrome",
    "firefox":       "firefox",
    "edge":          "msedge",
    "brave":         "brave",
    # Dev
    "vscode":        "code",
    "code":          "code",
    "visual studio code": "code",
    "notepad":       "notepad",
    "notepad++":     "notepad++",
    "sublime":       "subl",
    "cursor":        "cursor",
    # Terminal
    "terminal":      "wt",           # Windows Terminal
    "cmd":           "cmd",
    "powershell":    "powershell",
    "pwsh":          "pwsh",
    # Utilities
    "explorer":      "explorer",
    "file explorer": "explorer",
    "calculator":    "calc",
    "task manager":  "taskmgr",
    "control panel": "control",
    # Communication
    "discord":       "discord",
    "slack":         "slack",
    "teams":         "teams",
    "zoom":          "zoom",
    "spotify":       "spotify",
}


async def open_app(args: Dict[str, Any]) -> str:
    """Open a desktop application by name."""
    app_name = (args.get("app_name") or args.get("name") or "").strip()
    if not app_name:
        return "❌ open_app: No app_name provided."

    executable = _APP_ALIASES.get(app_name.lower(), app_name)

    # Check if executable is on PATH
    resolved = shutil.which(executable)
    if not resolved:
        # Try common Windows app locations
        candidates = [
            rf"C:\Program Files\{app_name}\{executable}.exe",
            rf"C:\Program Files (x86)\{app_name}\{executable}.exe",
            os.path.join(os.getenv("LOCALAPPDATA", ""), executable, f"{executable}.exe"),
        ]
        for c in candidates:
            if os.path.isfile(c):
                resolved = c
                break

    if not resolved and sys.platform == "win32":
        # Use Windows 'start' as last resort
        try:
            subprocess.Popen(
                f'start "" "{executable}"',
                shell=True,
                close_fds=True,
            )
            return f"✅ Launched '{app_name}' via shell."
        except Exception as e:
            return f"❌ Could not launch '{app_name}': {e}"

    if not resolved:
        return f"❌ Application '{app_name}' not found on PATH."

    try:
        subprocess.Popen([resolved], close_fds=True)
        return f"✅ Launched '{app_name}' ({resolved})"
    except Exception as e:
        return f"❌ Failed to launch '{app_name}': {e}"


async def open_url(args: Dict[str, Any]) -> str:
    """Open a URL in the default browser."""
    url = (args.get("url") or args.get("href") or "").strip()
    if not url:
        return "❌ open_url: No url provided."
    if not url.startswith(("http://", "https://", "file://")):
        url = "https://" + url
    try:
        webbrowser.open(url)
        return f"✅ Opened URL: {url}"
    except Exception as e:
        return f"❌ Could not open URL '{url}': {e}"


async def run_command(args: Dict[str, Any]) -> str:
    """
    Execute a shell command. AMBER risk — always requires confirmation.
    Captures stdout/stderr and returns combined output (max 4 KB).
    """
    cmd = (args.get("command") or args.get("cmd") or "").strip()
    if not cmd:
        return "❌ run_command: No command provided."

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        out = (stdout or b"").decode(errors="replace")
        err = (stderr or b"").decode(errors="replace")
        combined = (out + err).strip()
        if len(combined) > 4096:
            combined = combined[:4096] + "\n…[truncated]"
        exit_code = proc.returncode
        status = "✅" if exit_code == 0 else f"⚠️ exit={exit_code}"
        return f"{status}\n{combined}" if combined else f"{status} (no output)"
    except asyncio.TimeoutError:
        return "❌ run_command: Timed out after 30s."
    except Exception as e:
        return f"❌ run_command error: {e}"


# ── Tool definitions ──────────────────────────────────────────────────────────

desktop_tools = [
    ToolDefinition(
        name="open_app",
        handler=open_app,
        risk_level=RiskLevel.GREEN,
        description="Open a desktop application by name (e.g. 'code', 'chrome', 'terminal').",
    ),
    ToolDefinition(
        name="open_url",
        handler=open_url,
        risk_level=RiskLevel.GREEN,
        description="Open a URL in the default browser.",
    ),
    ToolDefinition(
        name="run_command",
        handler=run_command,
        risk_level=_AMBER,
        description="Execute a shell command on the host OS. Requires confirmation.",
    ),
]
