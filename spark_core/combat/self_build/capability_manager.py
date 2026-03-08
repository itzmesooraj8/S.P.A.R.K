"""
SPARK Self-Build — Capability Manager
=======================================
Detects which external tools are installed and available, reports which are
missing, and — with explicit operator approval — executes pip/system installs.

All install commands are hardcoded; arbitrary shell execution is NOT supported.
Only approved tool names from the KNOWN_CAPABILITIES whitelist can be installed.
"""
import asyncio
import shutil
import logging
import sys
from typing import TypedDict, Optional

log = logging.getLogger(__name__)


class CapabilityEntry(TypedDict):
    name:        str
    description: str
    install_cmd: list[str]
    check_cmd:   Optional[str]   # binary name to check in PATH; None = check via import
    check_module: Optional[str]  # Python module to try importing
    category:    str


# ── Approved capabilities whitelist ──────────────────────────────────────────
KNOWN_CAPABILITIES: dict[str, CapabilityEntry] = {
    "sherlock": {
        "name":         "Sherlock",
        "description":  "OSINT username search across 400+ social networks",
        "install_cmd":  [sys.executable, "-m", "pip", "install", "sherlock-project"],
        "check_cmd":    "sherlock",
        "check_module": None,
        "category":     "IDENTITY",
    },
    "holehe": {
        "name":         "Holehe",
        "description":  "Email-to-account correlation across 120+ services",
        "install_cmd":  [sys.executable, "-m", "pip", "install", "holehe"],
        "check_cmd":    "holehe",
        "check_module": None,
        "category":     "IDENTITY",
    },
    "theharvester": {
        "name":         "theHarvester",
        "description":  "Passive email/subdomain/IP harvesting from public sources",
        "install_cmd":  [sys.executable, "-m", "pip", "install", "theHarvester"],
        "check_cmd":    "theHarvester",
        "check_module": None,
        "category":     "RECON",
    },
    "shodan_sdk": {
        "name":         "Shodan Python SDK",
        "description":  "Python library for Shodan internet scan API",
        "install_cmd":  [sys.executable, "-m", "pip", "install", "shodan"],
        "check_cmd":    None,
        "check_module": "shodan",
        "category":     "RECON",
    },
    "vt-py": {
        "name":         "VirusTotal Python SDK",
        "description":  "Python library for VirusTotal malware scan API",
        "install_cmd":  [sys.executable, "-m", "pip", "install", "vt-py"],
        "check_cmd":    None,
        "check_module": "vt",
        "category":     "SIGINT",
    },
    "httpx_socks": {
        "name":         "httpx[socks]",
        "description":  "SOCKS5 proxy support for httpx — required for Tor connectivity",
        "install_cmd":  [sys.executable, "-m", "pip", "install", "httpx[socks]"],
        "check_cmd":    None,
        "check_module": "httpx",
        "category":     "TOR",
    },
    "aiosqlite": {
        "name":         "aiosqlite",
        "description":  "Async SQLite — required for local CVE index",
        "install_cmd":  [sys.executable, "-m", "pip", "install", "aiosqlite"],
        "check_cmd":    None,
        "check_module": "aiosqlite",
        "category":     "SIGINT",
    },
    "psutil": {
        "name":         "psutil",
        "description":  "System/process utilities — improves VPN interface detection",
        "install_cmd":  [sys.executable, "-m", "pip", "install", "psutil"],
        "check_cmd":    None,
        "check_module": "psutil",
        "category":     "OPSEC",
    },
}


def _is_installed(cap: CapabilityEntry) -> bool:
    if cap["check_cmd"]:
        return shutil.which(cap["check_cmd"]) is not None
    if cap["check_module"]:
        try:
            __import__(cap["check_module"])
            return True
        except ImportError:
            return False
    return False


def get_capability_status() -> dict:
    status = {}
    for key, cap in KNOWN_CAPABILITIES.items():
        installed = _is_installed(cap)
        status[key] = {
            "name":        cap["name"],
            "description": cap["description"],
            "category":    cap["category"],
            "installed":   installed,
            "install_cmd": " ".join(cap["install_cmd"]),
        }
    counts = {"installed": sum(1 for v in status.values() if v["installed"]),
              "missing":   sum(1 for v in status.values() if not v["installed"])}
    return {"capabilities": status, "summary": counts}


async def request_install(capability_key: str) -> dict:
    """Install a capability by key. Only whitelisted tools are accepted."""
    cap = KNOWN_CAPABILITIES.get(capability_key)
    if not cap:
        return {
            "status":  "UNKNOWN_CAPABILITY",
            "message": f"'{capability_key}' is not a known capability. "
                       f"Valid keys: {sorted(KNOWN_CAPABILITIES.keys())}",
        }

    if _is_installed(cap):
        return {"status": "ALREADY_INSTALLED", "capability": capability_key}

    log.info("Installing capability: %s → %s", capability_key, cap["install_cmd"])
    try:
        proc = await asyncio.create_subprocess_exec(
            *cap["install_cmd"],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=300)
        output = stdout.decode("utf-8", errors="replace") if stdout else ""

        if proc.returncode == 0:
            return {
                "status":     "INSTALLED",
                "capability": capability_key,
                "output":     output[-2000:],
            }
        return {
            "status":      "INSTALL_FAILED",
            "capability":  capability_key,
            "return_code": proc.returncode,
            "output":      output[-2000:],
        }
    except asyncio.TimeoutError:
        return {"status": "INSTALL_TIMEOUT", "capability": capability_key}
    except Exception as e:
        log.exception("Install failed for '%s'", capability_key)
        return {"status": "ERROR", "capability": capability_key, "error": str(e)}
