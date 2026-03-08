"""
SPARK Recon Engine — Passive Reconnaissance
============================================
Passive recon gathers intelligence WITHOUT sending any packets directly to
the target. All queries are made against public APIs or third-party indexes.

Modules:
  • shodan   — internet-wide scan data (requires SHODAN_API_KEY)
  • harvester — theHarvester subprocess wrapper (emails, subdomains, IP ranges)
  • subfinder — fast passive subdomain enumeration

None of these modules require the target to be in scope (no direct packets),
but scope enforcement may still be applied upstream at the router layer.
"""
import asyncio
import json
import logging
import os
import shutil
from typing import Optional

log = logging.getLogger(__name__)

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False

_SHODAN_BASE = "https://api.shodan.io"
_TIMEOUT     = 20


# ── Shodan ─────────────────────────────────────────────────────────────────────

async def _shodan_host(target: str) -> dict:
    api_key = os.environ.get("SHODAN_API_KEY", "")
    if not api_key:
        return {"available": False, "reason": "SHODAN_API_KEY not set in environment."}
    if not _HTTPX:
        return {"available": False, "reason": "httpx not installed."}

    import re, socket
    # Resolve hostname to IP for Shodan host lookup
    ip = target
    if not re.fullmatch(r"[\d\.]+", target):
        try:
            ip = socket.gethostbyname(target)
        except socket.gaierror:
            return {"error": f"Cannot resolve '{target}' to IP."}

    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"{_SHODAN_BASE}/shodan/host/{ip}",
                params={"key": api_key},
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "ip":           ip,
                    "org":          data.get("org"),
                    "country":      data.get("country_name"),
                    "city":         data.get("city"),
                    "isp":          data.get("isp"),
                    "os":           data.get("os"),
                    "ports":        data.get("ports", []),
                    "hostnames":    data.get("hostnames", []),
                    "vulns":        list(data.get("vulns", {}).keys()),
                    "tags":         data.get("tags", []),
                    "last_update":  data.get("last_update"),
                }
            return {"error": f"Shodan HTTP {r.status_code}: {r.text[:200]}"}
        except Exception as e:
            return {"error": str(e)}


async def _shodan_search(query: str) -> dict:
    api_key = os.environ.get("SHODAN_API_KEY", "")
    if not api_key or not _HTTPX:
        return {"available": False}
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(
                f"{_SHODAN_BASE}/shodan/host/search",
                params={"key": api_key, "query": query, "minify": "true"},
                timeout=_TIMEOUT,
            )
            if r.status_code == 200:
                data = r.json()
                return {
                    "total":   data.get("total", 0),
                    "matches": [
                        {
                            "ip":      m.get("ip_str"),
                            "port":    m.get("port"),
                            "org":     m.get("org"),
                            "country": m.get("location", {}).get("country_name"),
                        }
                        for m in data.get("matches", [])[:25]
                    ],
                }
            return {"error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"error": str(e)}


# ── theHarvester ───────────────────────────────────────────────────────────────

async def _run_harvester(target: str) -> dict:
    if not shutil.which("theHarvester"):
        return {
            "available": False,
            "reason":    "theHarvester not found in PATH. Install: pip install theHarvester",
        }
    try:
        proc = await asyncio.create_subprocess_exec(
            "theHarvester",
            "-d", target,
            "-b", "all",
            "-l", "100",
            "-f", "/dev/null",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode("utf-8", errors="replace")
        return {"available": True, "raw_output": output[:4000]}
    except asyncio.TimeoutError:
        return {"available": True, "error": "theHarvester timed out after 120s"}
    except Exception as e:
        return {"available": True, "error": str(e)}


# ── Subfinder ─────────────────────────────────────────────────────────────────

async def _run_subfinder(target: str) -> dict:
    if not shutil.which("subfinder"):
        return {
            "available": False,
            "reason":    "subfinder not found in PATH. Install via: go install -v github.com/projectdiscovery/subfinder/v2/cmd/subfinder@latest",
        }
    try:
        proc = await asyncio.create_subprocess_exec(
            "subfinder",
            "-d", target,
            "-silent",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=90)
        subdomains = [
            line.strip()
            for line in stdout.decode("utf-8", errors="replace").splitlines()
            if line.strip()
        ]
        return {"available": True, "subdomains": subdomains, "count": len(subdomains)}
    except asyncio.TimeoutError:
        return {"available": True, "error": "subfinder timed out after 90s"}
    except Exception as e:
        return {"available": True, "error": str(e)}


# ── Aggregated passive recon ───────────────────────────────────────────────────

async def run_passive_recon(target: str, modules: list[str]) -> dict:
    """Run selected passive recon modules concurrently and aggregate results."""
    tasks = {}

    if "shodan" in modules:
        tasks["shodan_host"]   = _shodan_host(target)
        tasks["shodan_search"] = _shodan_search(f"hostname:{target}")

    if "harvester" in modules:
        tasks["harvester"] = _run_harvester(target)

    if "subfinder" in modules:
        tasks["subfinder"] = _run_subfinder(target)

    if not tasks:
        return {"target": target, "error": "No valid modules specified."}

    keys            = list(tasks.keys())
    results_list    = await asyncio.gather(*tasks.values(), return_exceptions=True)
    results: dict   = {"target": target, "modules": {}}

    for k, res in zip(keys, results_list):
        if isinstance(res, Exception):
            results["modules"][k] = {"error": str(res)}
        else:
            results["modules"][k] = res

    return results
