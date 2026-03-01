"""
SPARK Security & Firewall Router
Provides real system-level security telemetry via psutil.
Endpoints:
  GET  /api/security/status   — ports, connections, top processes, threat level
  GET  /api/security/network  — top network I/O consumers
  POST /api/security/scan     — trigger a quick port/connection rescan
"""
import time
import socket
import psutil
from fastapi import APIRouter

router = APIRouter(prefix="/api/security", tags=["security"])

# Simple in-memory blocked IP set (persists for the server lifetime)
_blocked_ips: set[str] = set()
_last_scan: dict = {}


def _get_listening_ports() -> list[dict]:
    ports = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "LISTEN" and conn.laddr:
                ports.append({
                    "port": conn.laddr.port,
                    "addr": conn.laddr.ip,
                    "pid": conn.pid,
                    "process": _pid_name(conn.pid),
                })
    except Exception:
        pass
    # Deduplicate by port
    seen = set()
    unique = []
    for p in ports:
        if p["port"] not in seen:
            seen.add(p["port"])
            unique.append(p)
    return sorted(unique, key=lambda x: x["port"])[:20]


def _get_active_connections() -> dict:
    try:
        conns = psutil.net_connections(kind="inet")
        established = [c for c in conns if c.status == "ESTABLISHED"]
        external = [
            c for c in established
            if c.raddr and not c.raddr.ip.startswith(("127.", "::1", "0.0.0.0"))
        ]
        unique_hosts = list({c.raddr.ip for c in external if c.raddr})[:10]
        blocked_hits = [ip for ip in unique_hosts if ip in _blocked_ips]
        return {
            "total": len(conns),
            "established": len(established),
            "external_hosts": unique_hosts,
            "blocked_hits": blocked_hits,
        }
    except Exception:
        return {"total": 0, "established": 0, "external_hosts": [], "blocked_hits": []}


def _get_top_processes(n: int = 8) -> list[dict]:
    procs = []
    try:
        for p in psutil.process_iter(["pid", "name", "cpu_percent", "memory_percent", "status"]):
            try:
                procs.append({
                    "pid": p.info["pid"],
                    "name": p.info["name"],
                    "cpu": round(p.info["cpu_percent"] or 0, 1),
                    "mem": round(p.info["memory_percent"] or 0, 1),
                    "status": p.info["status"],
                    "risk": _assess_risk(p.info["name"]),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return sorted(procs, key=lambda x: x["cpu"], reverse=True)[:n]


def _get_net_io() -> dict:
    try:
        io = psutil.net_io_counters()
        return {
            "bytes_sent_mb": round(io.bytes_sent / 1_048_576, 2),
            "bytes_recv_mb": round(io.bytes_recv / 1_048_576, 2),
            "packets_sent": io.packets_sent,
            "packets_recv": io.packets_recv,
            "errin": io.errin,
            "errout": io.errout,
            "dropin": io.dropin,
            "dropout": io.dropout,
        }
    except Exception:
        return {}


def _pid_name(pid) -> str:
    if not pid:
        return "system"
    try:
        return psutil.Process(pid).name()
    except Exception:
        return "unknown"


_HIGH_RISK_NAMES = {"nc", "netcat", "nmap", "wireshark", "tcpdump", "meterpreter",
                    "mimikatz", "powersploit", "cobaltstrike", "metasploit"}

def _assess_risk(name: str) -> str:
    if not name:
        return "LOW"
    n = name.lower().replace(".exe", "")
    if n in _HIGH_RISK_NAMES:
        return "CRITICAL"
    if any(kw in n for kw in ("hack", "crack", "spy", "keylog", "inject")):
        return "HIGH"
    return "LOW"


@router.get("/status")
async def get_security_status():
    """Returns full real-time security telemetry."""
    global _last_scan
    _last_scan = {
        "timestamp": time.time(),
        "listening_ports": _get_listening_ports(),
        "connections": _get_active_connections(),
        "top_processes": _get_top_processes(),
        "net_io": _get_net_io(),
        "blocked_ips": list(_blocked_ips),
        "threat_level": _compute_threat_level(),
    }
    return _last_scan


@router.get("/network")
async def get_network_io():
    """Returns per-interface network statistics."""
    try:
        ifaces = []
        for iface, stats in psutil.net_if_stats().items():
            io = psutil.net_io_counters(pernic=True).get(iface)
            ifaces.append({
                "interface": iface,
                "is_up": stats.isup,
                "speed_mbps": stats.speed,
                "mtu": stats.mtu,
                "bytes_sent_mb": round(io.bytes_sent / 1_048_576, 2) if io else 0,
                "bytes_recv_mb": round(io.bytes_recv / 1_048_576, 2) if io else 0,
            })
        return {"interfaces": ifaces, "timestamp": time.time()}
    except Exception as e:
        return {"interfaces": [], "error": str(e)}


@router.post("/scan")
async def trigger_scan():
    """Trigger a fresh security scan synchronously."""
    return await get_security_status()


@router.post("/block/{ip}")
async def block_ip(ip: str):
    """Mark an IP as blocked (in-memory; cosmetic firewall rule)."""
    try:
        socket.inet_aton(ip)  # Validate IP
    except socket.error:
        return {"error": "Invalid IP address"}
    _blocked_ips.add(ip)
    return {"status": "blocked", "ip": ip, "total_blocked": len(_blocked_ips)}


@router.delete("/block/{ip}")
async def unblock_ip(ip: str):
    _blocked_ips.discard(ip)
    return {"status": "unblocked", "ip": ip}


def _compute_threat_level() -> str:
    """Heuristic threat level based on live system state."""
    conns = _get_active_connections()
    procs = _get_top_processes(20)
    if any(p["risk"] == "CRITICAL" for p in procs):
        return "CRITICAL"
    if len(conns["external_hosts"]) > 15 or conns["blocked_hits"]:
        return "HIGH"
    if len(conns["external_hosts"]) > 5:
        return "MEDIUM"
    return "LOW"
