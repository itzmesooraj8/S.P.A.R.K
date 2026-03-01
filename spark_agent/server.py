"""
spark_agent — Desktop Automation Agent
=======================================
Runs as a LOCAL-ONLY service on http://127.0.0.1:7700

Never bind to 0.0.0.0. This service has OS-level execution rights;
it must never be exposed to a network.

Two-step execution model
------------------------
1. POST /agent/plan   → returns what the agent intends to do
2. POST /agent/execute → runs it (or auto-approve via ALLOWLIST)

Quick-start:
  python -m spark_agent.server

Or from the project root:
  python spark_agent/server.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ─── Logging / audit ─────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s [agent] %(message)s")
log = logging.getLogger("spark_agent")

_AUDIT_LOG = Path(__file__).parent.parent / "spark_memory_db" / "agent_audit.jsonl"
_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)

def _audit(action: str, params: dict, result: str, success: bool):
    record = {
        "id": str(uuid.uuid4()),
        "ts": time.time(),
        "action": action,
        "params": params,
        "result": result,
        "success": success,
        "host": platform.node(),
    }
    with open(_AUDIT_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

# ─── Allowlist (auto-approve) ─────────────────────────────────────────────────
# Actions in the ALLOWLIST are executed without a separate confirm step.
# Everything else requires explicit user confirmation via /agent/confirm/{token}.

_ALLOWLIST: set[str] = {"open-url", "open-app"}  # run-command requires confirm

# ─── Pending confirmations ───────────────────────────────────────────────────

_pending: Dict[str, dict] = {}   # token → {action, params, expires}
_CONFIRM_TTL_S = 60              # tokens expire after 60 s

# ─── FastAPI app ─────────────────────────────────────────────────────────────

app = FastAPI(
    title="SPARK Desktop Agent",
    version="1.0.0",
    description="Local-only OS automation service. Bind: 127.0.0.1:7700",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080", "http://localhost:5173", "http://localhost:8000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Schemas ─────────────────────────────────────────────────────────────────

class OpenAppRequest(BaseModel):
    app_path: str                     # e.g. "notepad.exe" or full path
    args: List[str] = []

class OpenUrlRequest(BaseModel):
    url: str                          # must start with http:// or https://

class RunCommandRequest(BaseModel):
    command: str                      # shell command
    working_dir: Optional[str] = None
    timeout_s: int = 30               # max execution time

class ConfirmRequest(BaseModel):
    token: str

class PlanResponse(BaseModel):
    token: str
    action: str
    description: str
    auto_approved: bool
    expires_in_s: int = _CONFIRM_TTL_S

# ─── Tools ────────────────────────────────────────────────────────────────────

def _open_app(app_path: str, args: List[str]) -> str:
    """Launch an application by path (or name on PATH)."""
    resolved = shutil.which(app_path) or app_path
    if not Path(resolved).exists() and not shutil.which(app_path):
        raise ValueError(f"Application not found: {app_path!r}")

    if platform.system() == "Windows":
        subprocess.Popen([resolved] + args, creationflags=subprocess.DETACHED_PROCESS)
    else:
        subprocess.Popen([resolved] + args, start_new_session=True)
    return f"Launched {resolved}"


def _open_url(url: str) -> str:
    """Open a URL in the default system browser."""
    if not url.startswith(("http://", "https://")):
        raise ValueError("URL must start with http:// or https://")
    import webbrowser
    webbrowser.open(url)
    return f"Opened {url}"


def _run_command(command: str, working_dir: Optional[str], timeout_s: int) -> dict:
    """Run a shell command in a controlled subprocess."""
    cwd = working_dir or str(Path.home())
    result = subprocess.run(
        command,
        shell=True,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout_s,
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout[:4096],  # cap output
        "stderr": result.stderr[:1024],
    }


# ─── Plan step ───────────────────────────────────────────────────────────────

def _make_plan(action: str, params: dict, description: str) -> PlanResponse:
    token = str(uuid.uuid4())
    auto = action in _ALLOWLIST
    _pending[token] = {
        "action": action,
        "params": params,
        "expires": time.time() + _CONFIRM_TTL_S,
    }
    return PlanResponse(
        token=token,
        action=action,
        description=description,
        auto_approved=auto,
    )


async def _execute_pending(token: str) -> dict:
    """Actually run a pending action by token."""
    entry = _pending.pop(token, None)
    if not entry:
        raise HTTPException(status_code=404, detail="Token not found or expired")
    if time.time() > entry["expires"]:
        raise HTTPException(status_code=410, detail="Confirmation token expired")

    action = entry["action"]
    params = entry["params"]
    try:
        if action == "open-app":
            result = _open_app(params["app_path"], params.get("args", []))
            _audit(action, params, result, True)
            return {"success": True, "result": result}

        elif action == "open-url":
            result = _open_url(params["url"])
            _audit(action, params, result, True)
            return {"success": True, "result": result}

        elif action == "run-command":
            result = _run_command(
                params["command"],
                params.get("working_dir"),
                params.get("timeout_s", 30),
            )
            _audit(action, params, str(result), result["returncode"] == 0)
            return {"success": result["returncode"] == 0, "result": result}

        else:
            raise HTTPException(status_code=400, detail=f"Unknown action: {action}")

    except ValueError as e:
        _audit(action, params, str(e), False)
        raise HTTPException(status_code=422, detail=str(e))
    except subprocess.TimeoutExpired:
        _audit(action, params, "timeout", False)
        raise HTTPException(status_code=408, detail="Command timed out")


# ─── Endpoints ───────────────────────────────────────────────────────────────

@app.get("/agent/health")
def health():
    return {"status": "ok", "service": "spark_agent", "version": "1.0.0", "host": platform.node()}

@app.get("/agent/tools")
def list_tools():
    return {
        "tools": [
            {"name": "open-app",     "description": "Launch an application by path or name", "requires_confirm": False},
            {"name": "open-url",     "description": "Open a URL in the default browser",     "requires_confirm": False},
            {"name": "run-command",  "description": "Execute a shell command",                "requires_confirm": True},
        ]
    }

@app.post("/agent/open-app")
async def plan_open_app(req: OpenAppRequest):
    """Plan (and auto-execute) opening an application."""
    plan = _make_plan("open-app", req.model_dump(), f"Open '{req.app_path}' {' '.join(req.args)}")
    if plan.auto_approved:
        result = await _execute_pending(plan.token)
        return {**plan.model_dump(), **result}
    return plan

@app.post("/agent/open-url")
async def plan_open_url(req: OpenUrlRequest):
    """Plan (and auto-execute) opening a URL."""
    plan = _make_plan("open-url", req.model_dump(), f"Open URL: {req.url}")
    if plan.auto_approved:
        result = await _execute_pending(plan.token)
        return {**plan.model_dump(), **result}
    return plan

@app.post("/agent/run-command")
async def plan_run_command(req: RunCommandRequest):
    """
    Plan running a shell command.
    Returns a token that must be confirmed via POST /agent/confirm/{token}
    before execution begins.
    """
    plan = _make_plan(
        "run-command",
        req.model_dump(),
        f"Run shell command: {req.command[:120]}"
    )
    # run-command is NOT in the allowlist — always requires manual confirm
    return plan

@app.post("/agent/confirm/{token}")
async def confirm_action(token: str):
    """Execute a pending action after user confirmation."""
    return await _execute_pending(token)

@app.delete("/agent/confirm/{token}")
async def cancel_action(token: str):
    """Cancel a pending action without executing it."""
    removed = _pending.pop(token, None)
    if not removed:
        raise HTTPException(status_code=404, detail="Token not found")
    _audit(removed["action"], removed["params"], "cancelled_by_user", False)
    return {"status": "cancelled", "action": removed["action"]}

@app.get("/agent/audit")
async def get_audit_log(limit: int = 50):
    """Return the last N audit log entries."""
    if not _AUDIT_LOG.exists():
        return {"entries": []}
    lines = _AUDIT_LOG.read_text(encoding="utf-8").strip().splitlines()
    recent = lines[-limit:]
    entries = []
    for line in recent:
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return {"entries": list(reversed(entries))}   # newest first


# ─── Entry point ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    log.info("🤖 [spark_agent] Starting local Desktop Agent on http://127.0.0.1:7700")
    uvicorn.run(
        "server:app",
        host="127.0.0.1",   # LOCAL ONLY — never 0.0.0.0
        port=7700,
        reload=False,
        log_level="info",
        app_dir=str(Path(__file__).parent),
    )
