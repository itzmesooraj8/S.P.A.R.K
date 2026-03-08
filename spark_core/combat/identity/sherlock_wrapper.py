"""
SPARK Identity Engine — Sherlock Username Hunter
=================================================
Wraps the Sherlock OSINT tool (https://github.com/sherlock-project/sherlock)
to search 400+ social networks for a given username.

If Sherlock is not installed, this module gracefully returns a capability-
request response so the frontend can prompt for installation.

Results are broadcast live via the SPARK WebSocket system so the operator
sees hits stream in real-time rather than waiting for the full scan.
"""
import asyncio
import json
import logging
import shutil
import uuid
from typing import Optional

log = logging.getLogger(__name__)

# Broadcast helper — optional import so unit tests don't require the full stack
try:
    from ws.manager import ws_manager
    _WS_AVAILABLE = True
except ImportError:
    _WS_AVAILABLE = False


def _sherlock_available() -> bool:
    return shutil.which("sherlock") is not None


async def start_username_hunt(username: str) -> str:
    """
    Launch a background Sherlock scan.
    Results are streamed to WebSocket clients under namespace 'combat'.
    Returns a job_id the frontend can use to correlate WS messages.
    """
    if not _sherlock_available():
        job_id = str(uuid.uuid4())
        _broadcast({
            "type":     "CAPABILITY_REQUIRED",
            "job_id":   job_id,
            "tool":     "sherlock",
            "install":  "pip install sherlock-project",
            "message":  "Sherlock is not installed. Use the Self-Build panel to install it.",
        })
        return job_id

    job_id = str(uuid.uuid4())
    asyncio.create_task(_run_sherlock(username, job_id))
    return job_id


async def _run_sherlock(username: str, job_id: str) -> None:
    """Run Sherlock as subprocess and stream JSON results via WebSocket."""
    _broadcast({"type": "HUNT_STARTED", "job_id": job_id, "username": username})
    try:
        proc = await asyncio.create_subprocess_exec(
            "sherlock",
            username,
            "--print-found",
            "--output", "/dev/null",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        assert proc.stdout is not None
        async for raw_line in proc.stdout:
            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            # Sherlock output format: "[+] Site: URL"
            if line.startswith("[+]"):
                parts = line[3:].strip().split(": ", 1)
                platform = parts[0].strip() if parts else "Unknown"
                url      = parts[1].strip() if len(parts) > 1 else ""
                _broadcast({
                    "type":     "HUNT_HIT",
                    "job_id":   job_id,
                    "username": username,
                    "platform": platform,
                    "url":      url,
                    "found":    True,
                })

        await proc.wait()
        _broadcast({
            "type":       "HUNT_COMPLETE",
            "job_id":     job_id,
            "username":   username,
            "return_code": proc.returncode,
        })
    except Exception as exc:
        log.exception("Sherlock scan failed for '%s': %s", username, exc)
        _broadcast({"type": "HUNT_ERROR", "job_id": job_id, "error": str(exc)})


def _broadcast(payload: dict) -> None:
    if _WS_AVAILABLE:
        try:
            asyncio.get_event_loop().create_task(
                ws_manager.broadcast(json.dumps(payload), "combat")
            )
        except RuntimeError:
            log.debug("No event loop for WS broadcast: %s", payload)
