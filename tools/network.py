"""Network security monitor."""

from __future__ import annotations

import socket

import psutil


def get_network_connections() -> list[dict]:
    """List all active network connections with process info."""
    connections: list[dict] = []
    for conn in psutil.net_connections(kind="inet"):
        try:
            proc = psutil.Process(conn.pid) if conn.pid else None
            connections.append(
                {
                    "pid": conn.pid,
                    "process": proc.name() if proc else "unknown",
                    "local": f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "",
                    "remote": f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "",
                    "status": conn.status,
                }
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return connections


def get_open_ports() -> list[dict]:
    """Return all listening ports with process details."""
    ports: list[dict] = []
    for conn in psutil.net_connections(kind="inet"):
        if conn.status == "LISTEN":
            try:
                process_name = psutil.Process(conn.pid).name() if conn.pid else "unknown"
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = "unknown"
            ports.append({"port": conn.laddr.port if conn.laddr else None, "pid": conn.pid, "process": process_name})
    return ports


def scan_local_network() -> list[str]:
    """Scan the local /24 network for live hosts using nmap if available."""
    try:
        import nmap

        nm = nmap.PortScanner()
        nm.scan(hosts="192.168.1.0/24", arguments="-sn")
        return [host for host in nm.all_hosts()]
    except ImportError:
        return ["nmap not installed"]
    except Exception as exc:
        return [f"Scan error: {exc}"]