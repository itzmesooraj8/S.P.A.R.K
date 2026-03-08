"""
SPARK Recon Engine — Active Reconnaissance
==========================================
Active recon sends direct packets to the target. All calls are gated behind
scope enforcement at the router layer; this module enforces it a second time
as defense-in-depth.

AUTHORIZATION REQUIRED: Each target must be declared in scope via
  /api/combat/opsec/scope/add   before any active scan will run.

Scan types:
  basic   — top 1000 ports, version detection, default scripts
  full    — all 65535 ports
  stealth — SYN scan (requires root/admin)
  vuln    — NSE vuln scripts (basic ports + script scanning)

Depends on: nmap binary in PATH
"""
import asyncio
import json
import logging
import shutil
from typing import Any

from ..opsec.scope_enforcer import scope_enforcer, OutOfScopeError

log = logging.getLogger(__name__)

# Nmap argument presets per scan type
_NMAP_PRESETS: dict[str, list[str]] = {
    "basic":   ["-sV", "-sC", "--top-ports", "1000", "-T4"],
    "full":    ["-sV", "-sC", "-p-", "-T3"],
    "stealth": ["-sS", "-sV", "--top-ports", "1000", "-T2"],
    "vuln":    ["-sV", "--script", "vuln", "--top-ports", "1000", "-T4"],
}


def _nmap_available() -> bool:
    return shutil.which("nmap") is not None


def _parse_nmap_xml(xml_output: str) -> list[dict[str, Any]]:
    """Parse basic host/port data from nmap XML output."""
    try:
        import xml.etree.ElementTree as ET
        root  = ET.fromstring(xml_output)
        hosts = []
        for host in root.findall("host"):
            addr_el  = host.find("address")
            address  = addr_el.get("addr") if addr_el is not None else "unknown"
            status   = host.find("status")
            state    = status.get("state") if status is not None else "unknown"
            ports    = []
            ports_el = host.find("ports")
            if ports_el:
                for port_el in ports_el.findall("port"):
                    state_el   = port_el.find("state")
                    service_el = port_el.find("service")
                    ports.append({
                        "portid":   int(port_el.get("portid", 0)),
                        "protocol": port_el.get("protocol"),
                        "state":    state_el.get("state")    if state_el   is not None else "unknown",
                        "service":  service_el.get("name")   if service_el is not None else "",
                        "version":  service_el.get("version") if service_el is not None else "",
                        "product":  service_el.get("product") if service_el is not None else "",
                    })
            hosts.append({"address": address, "state": state, "ports": ports})
        return hosts
    except Exception as e:
        log.warning("nmap XML parse error: %s", e)
        return []


async def run_active_recon(target: str, scan_type: str = "basic") -> dict:
    """Run an nmap scan against an in-scope target."""
    # Double-check scope enforcement
    try:
        scope_enforcer.assert_in_scope(target)
    except OutOfScopeError as e:
        return {"error": "OUT_OF_SCOPE", "message": str(e)}

    if not _nmap_available():
        return {
            "available": False,
            "reason":    "nmap binary not found in PATH. Install nmap from https://nmap.org/",
            "target":    target,
        }

    preset = _NMAP_PRESETS.get(scan_type, _NMAP_PRESETS["basic"])
    args   = ["nmap", "-oX", "-"] + preset + [target]

    log.info("Active scan starting: nmap %s %s", " ".join(preset), target)

    try:
        proc = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=600)
        xml_output = stdout.decode("utf-8", errors="replace")
        hosts      = _parse_nmap_xml(xml_output)
        open_ports = []
        for h in hosts:
            for p in h.get("ports", []):
                if p.get("state") == "open":
                    open_ports.append(p)

        return {
            "target":    target,
            "scan_type": scan_type,
            "status":    "COMPLETE",
            "hosts":     hosts,
            "open_ports_count": len(open_ports),
            "open_ports": open_ports,
            "return_code": proc.returncode,
        }
    except asyncio.TimeoutError:
        return {"target": target, "scan_type": scan_type, "error": "Scan timed out after 600 seconds."}
    except Exception as e:
        log.exception("Active recon failed for '%s'", target)
        return {"target": target, "scan_type": scan_type, "error": str(e)}
