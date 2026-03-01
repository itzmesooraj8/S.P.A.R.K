"""
DesktopAgentTool — bridges SPARK core AI to the local spark_agent service.

The tool sends requests to http://127.0.0.1:7700 (local only).
For commands that require confirmation, it emits a CONFIRM_TOOL event
so the HUD can surface a confirmation prompt to the user.
"""

from __future__ import annotations
import json
from typing import Any, Dict

import httpx

from system.event_bus import event_bus

_AGENT_BASE = "http://127.0.0.1:7700"
_TIMEOUT    = 10.0   # seconds


async def _post(path: str, body: dict) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
        r = await c.post(f"{_AGENT_BASE}{path}", json=body)
        r.raise_for_status()
        return r.json()


async def open_app(app_path: str, args: list[str] = []) -> str:
    """
    Open an application on the local machine.

    Args:
        app_path: executable name (on PATH) or full path to the binary.
        args: optional list of arguments to pass to the application.
    Returns: confirmation message.
    """
    result = await _post("/agent/open-app", {"app_path": app_path, "args": args})
    return result.get("result", str(result))


async def open_url(url: str) -> str:
    """
    Open a URL in the system's default browser.

    Args:
        url: must start with http:// or https://.
    Returns: confirmation message.
    """
    result = await _post("/agent/open-url", {"url": url})
    return result.get("result", str(result))


async def run_command(
    command: str,
    working_dir: str | None = None,
    timeout_s: int = 30,
) -> str:
    """
    Plan running a shell command on the local machine.
    The command will NOT run until the user confirms it in the HUD.

    Args:
        command: the shell command to run.
        working_dir: optional working directory (defaults to user home).
        timeout_s: maximum seconds to wait for completion (default 30).
    Returns: a pending token that the user must confirm.
    """
    plan = await _post("/agent/run-command", {
        "command": command,
        "working_dir": working_dir,
        "timeout_s": timeout_s,
    })

    token    = plan.get("token", "?")
    desc     = plan.get("description", command)

    # Emit event so HUD shows a confirm/cancel prompt
    event_bus.publish("confirm_tool", {
        "tool":       "run_command",
        "arguments":  {"command": command, "working_dir": working_dir},
        "risk_level": "HIGH",
        "token":      token,
        "description": desc,
    })

    return (
        f"⏳ Command staged for confirmation. Token: {token}\n"
        f"Command: {command}\n"
        f"Confirm in the HUD or call POST /agent/confirm/{token}"
    )


async def confirm_command(token: str) -> str:
    """
    Execute a previously staged shell command (after user confirmed it).

    Args:
        token: the confirmation token returned by run_command.
    Returns: command output.
    """
    async with httpx.AsyncClient(timeout=60.0) as c:
        r = await c.post(f"{_AGENT_BASE}/agent/confirm/{token}")
        r.raise_for_status()
        data = r.json()

    if data.get("success"):
        inner = data.get("result", {})
        if isinstance(inner, dict):
            stdout = inner.get("stdout", "")
            stderr = inner.get("stderr", "")
            rc     = inner.get("returncode", 0)
            return f"Exit {rc}\n{stdout}" + (f"\n[stderr] {stderr}" if stderr else "")
        return str(inner)
    return f"Command failed: {data}"


async def agent_health() -> dict:
    """Check if the local Desktop Agent service is running."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get(f"{_AGENT_BASE}/agent/health")
            return r.json()
    except Exception as e:
        return {"status": "offline", "error": str(e)}
