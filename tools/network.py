"""Network security monitor."""

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
    """List all open listening ports on this machine."""
    ports: list[dict] = []
    for conn in psutil.net_connections(kind="inet"):
        if conn.status == "LISTEN":
            ports.append(
                {
                    "port": conn.laddr.port,
                    "pid": conn.pid,
                    "process": psutil.Process(conn.pid).name() if conn.pid else "unknown",
                }
            )
    return ports


def scan_local_network() -> list[str]:
    """
    Scan your local network for connected devices.
    Only works on devices you own — legal on your own WiFi.
    Requires: pip install python-nmap
    """
    try:
        import nmap

        nm = nmap.PortScanner()
        nm.scan(hosts="192.168.1.0/24", arguments="-sn")
        return [host for host in nm.all_hosts()]
    except ImportError:
        return ["nmap not installed. Run: pip install python-nmap"]
    except Exception as exc:
        return [f"Scan error: {exc}"]