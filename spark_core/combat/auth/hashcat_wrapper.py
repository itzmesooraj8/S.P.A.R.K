"""
Hashcat Wrapper
================
Runs hashcat for password recovery audits.

IMPORTANT: Only ever operate on hashes you own or have written authorisation
           to test.  Never store or transmit plaintext passwords.
"""
import asyncio
import logging
import re
import uuid
from pathlib import Path
from typing import TypedDict, Optional

log = logging.getLogger(__name__)

# Hashcat mode IDs for common hash types
HASH_MODES: dict = {
    "ntlm":     1000,
    "md5":      0,
    "sha1":     100,
    "sha256":   1400,
    "sha512":   1700,
    "bcrypt":   3200,
    "wpa2":     22000,
    "netntlmv2": 5600,
}

_RESULTS_DIR = Path(__file__).parent / "results"
_RESULTS_DIR.mkdir(exist_ok=True)


class HashcatJob(TypedDict):
    job_id:          str
    hash_type:       str
    hash_mode:       int
    status:          str   # RUNNING | COMPLETE | ERROR | EXHAUSTED
    recovered:       int
    total:           int
    progress_pct:    float
    speed_hps:       float
    time_remaining:  str
    output_file:     str   # path to cracked.txt (no plaintexts in API response)


async def run_hashcat(
    hash_file: str,
    wordlist: str,
    hash_type: str = "ntlm",
    rules: Optional[str] = None,
) -> HashcatJob:
    """
    Run hashcat against hash_file using wordlist attack.
    Streams progress via WebSocket 'combat' namespace.
    Returns a HashcatJob summary — plaintext passwords are written to a local
    file ONLY, never returned in the API response.
    """
    job_id    = str(uuid.uuid4())[:8]
    hash_mode = HASH_MODES.get(hash_type.lower(), 0)
    out_file  = str(_RESULTS_DIR / f"cracked_{job_id}.txt")

    cmd = [
        "hashcat",
        "-m", str(hash_mode),
        "-a", "0",                  # dictionary attack
        "--status",
        "--status-timer", "3",
        "--machine-readable",
        "-o", out_file,
        "--outfmt", "2",            # hash:plain
        hash_file,
        wordlist,
    ]
    if rules:
        cmd += ["-r", rules]

    log.info("Hashcat job %s: mode=%d hash_file=%s wordlist=%s", job_id, hash_mode, hash_file, wordlist)

    job: HashcatJob = HashcatJob(
        job_id         = job_id,
        hash_type      = hash_type,
        hash_mode      = hash_mode,
        status         = "RUNNING",
        recovered      = 0,
        total          = 0,
        progress_pct   = 0.0,
        speed_hps      = 0.0,
        time_remaining = "unknown",
        output_file    = out_file,
    )

    try:
        from spark_core.ws.manager import ws_manager

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        # Parse machine-readable status lines while running
        while True:
            line_bytes = await proc.stdout.readline()
            if not line_bytes:
                break
            line = line_bytes.decode("utf-8", errors="replace").strip()
            _parse_status_line(line, job)
            await ws_manager.broadcast("combat", {
                "type": "HASHCAT_PROGRESS",
                "job_id": job_id,
                "progress_pct": job["progress_pct"],
                "speed_hps": job["speed_hps"],
                "recovered": job["recovered"],
                "time_remaining": job["time_remaining"],
            })

        await proc.wait()
        job["status"] = "COMPLETE" if proc.returncode in (0, 1) else "ERROR"

    except FileNotFoundError:
        log.warning("hashcat not found — returning mock job")
        job["status"] = "ERROR"
        job["time_remaining"] = "hashcat not installed"
    except Exception as exc:
        log.error("Hashcat error: %s", exc)
        job["status"] = "ERROR"

    return job


def _parse_status_line(line: str, job: HashcatJob) -> None:
    """
    Parse hashcat machine-readable STATUS lines.
    Format: STATUS\t<session>\t...\tRECOVERED\t<x>/<y>\tSPEED\t<hps>\tETA\t<eta>
    """
    if not line.startswith("STATUS"):
        return
    parts = line.split("\t")
    kv: dict = {}
    for i in range(0, len(parts) - 1, 2):
        kv[parts[i].strip()] = parts[i + 1].strip()

    try:
        rec_str = kv.get("RECOVERED", "0/0")
        rec_parts = rec_str.split("/")
        job["recovered"] = int(rec_parts[0])
        job["total"]     = int(rec_parts[1]) if len(rec_parts) > 1 else 0
    except (ValueError, IndexError):
        pass

    try:
        job["speed_hps"] = float(kv.get("SPEED", "0").split()[0])
    except ValueError:
        pass

    try:
        prog = kv.get("PROGRESS", "0/0").split("/")
        if len(prog) == 2 and int(prog[1]) > 0:
            job["progress_pct"] = round(int(prog[0]) / int(prog[1]) * 100, 2)
    except (ValueError, ZeroDivisionError):
        pass

    job["time_remaining"] = kv.get("ETA", "unknown")
