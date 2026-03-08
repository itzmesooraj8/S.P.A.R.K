"""
SPARK Self-Build — Technique Effectiveness Scorer
==================================================
Tracks which recon/exploitation techniques were effective against particular
target types and maintains a JSONL learning log in spark_dev_memory/.

This enables SPARK to recommend higher-probability techniques first
for a given target fingerprint.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

log         = logging.getLogger(__name__)
_LOG_FILE   = Path(__file__).parent.parent.parent.parent / "spark_dev_memory" / "technique_scores.jsonl"


# ── Technique catalogue ──────────────────────────────────────────────────────
_TECHNIQUES: list[dict] = [
    {
        "id":          "PASSIVE_SHODAN",
        "name":        "Shodan Host Lookup",
        "category":    "PASSIVE_RECON",
        "description": "Query Shodan for prior scan data without touching the target.",
        "tags":        ["shodan", "passive", "quick"],
    },
    {
        "id":          "PASSIVE_SUBFINDER",
        "name":        "Subfinder DNS Enumeration",
        "category":    "PASSIVE_RECON",
        "description": "Enumerate subdomains via passive DNS aggregation.",
        "tags":        ["dns", "subdomain", "passive"],
    },
    {
        "id":          "PASSIVE_HARVESTER",
        "name":        "theHarvester Email/IP Harvest",
        "category":    "PASSIVE_RECON",
        "description": "Gather emails, subdomains, and IPs from public sources.",
        "tags":        ["email", "passive", "multi-source"],
    },
    {
        "id":          "IDENTITY_USERNAME",
        "name":        "Sherlock Username Hunt",
        "category":    "IDENTITY",
        "description": "Search 400+ social platforms for a username.",
        "tags":        ["username", "social", "osint"],
    },
    {
        "id":          "IDENTITY_EMAIL",
        "name":        "Email Intel (Hunter + HIBP)",
        "category":    "IDENTITY",
        "description": "Verify email validity and check breach exposure.",
        "tags":        ["email", "breach", "hibp"],
    },
    {
        "id":          "ACTIVE_NMAP_BASIC",
        "name":        "Nmap Basic Scan",
        "category":    "ACTIVE_RECON",
        "description": "Top 1000 ports, version detection, default scripts.",
        "tags":        ["nmap", "port-scan", "active"],
    },
    {
        "id":          "ACTIVE_NMAP_VULN",
        "name":        "Nmap Vuln Script Scan",
        "category":    "ACTIVE_RECON",
        "description": "Run NSE vulnerability scripts against open ports.",
        "tags":        ["nmap", "vuln", "active"],
    },
    {
        "id":          "SIGINT_NVD",
        "name":        "NVD CVE Lookup",
        "category":    "SIGINT",
        "description": "Search NIST NVD for relevant CVEs matching the target software.",
        "tags":        ["cve", "nvd", "sigint"],
    },
    {
        "id":          "SIGINT_CISA",
        "name":        "CISA KEV Check",
        "category":    "SIGINT",
        "description": "Check if any CVEs affecting the target are in CISA KEV.",
        "tags":        ["cisa", "kev", "exploitation"],
    },
]


def get_all_techniques() -> list[dict]:
    """Return the technique catalogue with scored statistics appended."""
    scores = _load_scores()
    result = []
    for t in _TECHNIQUES:
        tid    = t["id"]
        events = scores.get(tid, [])
        total  = len(events)
        hits   = sum(1 for e in events if e.get("success"))
        result.append({
            **t,
            "uses":         total,
            "successes":    hits,
            "success_rate": round(hits / total * 100) if total else None,
        })
    return result


def record_technique_result(
    technique_id: str,
    target_type: str,
    success: bool,
    notes: str = "",
) -> None:
    """Append a technique result to the learning log."""
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "ts":           datetime.now(timezone.utc).isoformat(),
        "technique_id": technique_id,
        "target_type":  target_type,
        "success":      success,
        "notes":        notes,
    }
    with _LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


def _load_scores() -> dict[str, list[dict]]:
    """Load all log entries grouped by technique_id."""
    if not _LOG_FILE.exists():
        return {}
    grouped: dict[str, list[dict]] = {}
    for line in _LOG_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
            tid    = record.get("technique_id", "UNKNOWN")
            grouped.setdefault(tid, []).append(record)
        except json.JSONDecodeError:
            pass
    return grouped
