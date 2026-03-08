"""
Gyoithon Runner
================
Wraps the Gyoithon AI-driven web technology identification framework.
Gyoithon: https://github.com/gyoisamurai/GyoiThon

Install: git clone into tools/gyoithon/ or pip install gyoithon
Requires Python 3.8+ and scikit-learn / tensorflow in the venv.
"""
import asyncio
import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import List, Optional, TypedDict

log = logging.getLogger(__name__)

_GYOITHON_DIR = Path(__file__).parent.parent.parent / "tools" / "gyoithon"
_GYOITHON_MAIN = _GYOITHON_DIR / "gyoithon.py"


class GyoithonResult(TypedDict):
    target:       str
    raw_path:     str
    technologies: List[dict]   # [{name, version, confidence}]
    cves:         List[dict]   # [{cve_id, cvss, description}]
    status:       str


async def run_gyoithon(
    target_url: str,
    report_dir: Optional[str] = None,
) -> GyoithonResult:
    """
    Run Gyoithon against target_url.
    Returns parsed technology fingerprints and associated CVEs.
    """
    if report_dir is None:
        report_dir = tempfile.mkdtemp(prefix="gyoithon_")

    if not _GYOITHON_MAIN.exists():
        log.warning("Gyoithon not found at %s — returning empty result", _GYOITHON_MAIN)
        return GyoithonResult(
            target       = target_url,
            raw_path     = "",
            technologies = [],
            cves         = [],
            status       = "NOT_INSTALLED",
        )

    cmd = [
        "python", str(_GYOITHON_MAIN),
        "-u", target_url,
        "--report-dir", report_dir,
        "--silent",
    ]

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(_GYOITHON_DIR),
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        output = stdout.decode("utf-8", errors="replace")

        # Look for JSON report
        reports = list(Path(report_dir).glob("*.json"))
        if reports:
            raw_path = str(reports[-1])
            tech, cves = _parse_report(raw_path)
        else:
            raw_path = ""
            tech, cves = _parse_stdout(output)

        return GyoithonResult(
            target       = target_url,
            raw_path     = raw_path,
            technologies = tech,
            cves         = cves,
            status       = "COMPLETE",
        )
    except asyncio.TimeoutError:
        return GyoithonResult(
            target=target_url, raw_path="", technologies=[], cves=[], status="TIMEOUT"
        )
    except Exception as exc:
        log.error("Gyoithon error: %s", exc)
        return GyoithonResult(
            target=target_url, raw_path="", technologies=[], cves=[], status="ERROR"
        )


def _parse_report(path: str) -> tuple:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        tech = data.get("technologies", [])
        cves = data.get("cves", [])
        return tech, cves
    except Exception:
        return [], []


def _parse_stdout(output: str) -> tuple:
    """Best-effort extraction from stdout when no JSON report is produced."""
    tech = []
    cves = []
    for line in output.splitlines():
        if "Detected:" in line:
            parts = line.split("Detected:", 1)[1].strip()
            tech.append({"name": parts, "version": "", "confidence": 0.5})
        m = re.search(r"CVE-\d{4}-\d+", line)
        if m:
            cves.append({"cve_id": m.group(), "cvss": "", "description": line.strip()})
    return tech, cves
