"""
SPARK Identity Engine — Holehe Email-to-Account Correlation
============================================================
Holehe checks whether an email address is registered on 120+ services
(GitHub, Twitter, Netflix, etc.) using password-reset flows — no password required.

Docs: https://github.com/megadose/holehe
Install: pip install holehe
"""
import asyncio
import json
import logging
import shutil

log = logging.getLogger(__name__)


def _holehe_available() -> bool:
    return shutil.which("holehe") is not None


async def run_holehe(email: str) -> dict:
    """
    Run holehe for the given email and return a structured result dict.
    Falls back to a CAPABILITY_REQUIRED response if holehe is not installed.
    """
    if not _holehe_available():
        return {
            "status":   "CAPABILITY_REQUIRED",
            "tool":     "holehe",
            "install":  "pip install holehe",
            "message":  "Holehe is not installed. Use the Self-Build panel to install it.",
            "email":    email,
        }

    results = []
    errors  = []

    try:
        proc = await asyncio.create_subprocess_exec(
            "holehe",
            email,
            "--only-used",
            "--no-color",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        lines = stdout.decode("utf-8", errors="replace").splitlines()

        for line in lines:
            line = line.strip()
            # holehe output: "[+] twitter.com"  or  "[-] github.com"
            if line.startswith("[+]"):
                service = line[3:].strip()
                results.append({"service": service, "registered": True})
            elif line.startswith("[-]"):
                service = line[3:].strip()
                results.append({"service": service, "registered": False})

        if stderr:
            errors = stderr.decode("utf-8", errors="replace").strip().splitlines()

    except Exception as exc:
        log.exception("Holehe failed for '%s'", email)
        return {"status": "ERROR", "email": email, "error": str(exc)}

    registered = [r for r in results if r["registered"]]
    return {
        "status":       "COMPLETE",
        "email":        email,
        "total_checked": len(results),
        "registered_count": len(registered),
        "registered_on": [r["service"] for r in registered],
        "full_results": results,
        "errors":       errors,
    }
