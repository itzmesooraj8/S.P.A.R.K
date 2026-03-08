"""
SPARK OpSec — VPN, Tor, Shadowsocks & Privoxy Detection
=========================================================
Checks the full anonymity stack:
  • VPN   — interface name patterns (tun/wg/nordlynx etc.)
  • Tor   — Tor Project IP-check API
  • Shadowsocks — checks for ss-local process + SOCKS5 proxy at :1080/:1086
  • Privoxy — checks for privoxy process + HTTP proxy at :8118

Returns a layer stack with one of:
  TOR / SHADOWSOCKS / VPN / PRIVOXY / CLEARNET
"""
import re
import socket
import asyncio
import logging
import subprocess
import sys
from typing import TypedDict, List

try:
    import httpx
    _HTTPX_AVAILABLE = True
except ImportError:
    _HTTPX_AVAILABLE = False

log = logging.getLogger(__name__)

_VPN_IFACE_PATTERNS = re.compile(
    r"^(tun\d+|tap\d+|wg\d+|proton\d*|nordlynx|openvpn|utun\d+|ipsec\d*)",
    re.IGNORECASE,
)

TOR_CHECK_URL  = "https://check.torproject.org/api/ip"
IP_CHECK_URL   = "https://api.ipify.org"
TIMEOUT_SECS   = 8

# Shadowsocks default ports
_SS_PORTS = [1080, 1086, 1090]
# Privoxy default port
_PRIVOXY_PORT = 8118


class VpnCheckResult(TypedDict):
    vpn_detected:       bool
    tor_detected:       bool
    shadowsocks_detected: bool
    privoxy_detected:   bool
    public_ip:          str
    vpn_interfaces:     List[str]
    anonymity_layer:    str   # TOR | SHADOWSOCKS | VPN | PRIVOXY | CLEARNET
    exposed:            bool
    warning:            str


def _get_local_interfaces() -> List[str]:
    interfaces: List[str] = []
    try:
        import psutil  # type: ignore
        interfaces = list(psutil.net_if_addrs().keys())
    except ImportError:
        try:
            result = subprocess.run(
                ["ipconfig"] if sys.platform == "win32" else ["ip", "link"],
                capture_output=True, text=True, timeout=5
            )
            interfaces = re.findall(r"(?:^|\n)([A-Za-z][A-Za-z0-9_\-\.]+)(?:\s+|:)", result.stdout)
        except Exception:
            pass
    return interfaces


def _detect_vpn_interfaces() -> List[str]:
    return [i for i in _get_local_interfaces() if _VPN_IFACE_PATTERNS.search(i)]


def _detect_process(name: str) -> bool:
    """Return True if a process matching name is currently running."""
    try:
        import psutil  # type: ignore
        for p in psutil.process_iter(["name"]):
            if name.lower() in (p.info.get("name") or "").lower():
                return True
        return False
    except Exception:
        try:
            flag = "/C" if sys.platform == "win32" else "-c"
            cmd  = ["tasklist"] if sys.platform == "win32" else ["pgrep", "-x", name]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            return name.lower() in r.stdout.lower()
        except Exception:
            return False


def _detect_shadowsocks() -> bool:
    """Check for ss-local process OR SOCKS5 listener on known SS ports."""
    if _detect_process("ss-local") or _detect_process("sslocal"):
        return True
    for port in _SS_PORTS:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return True
        except Exception:
            pass
    return False


def _detect_privoxy() -> bool:
    """Check for privoxy process OR HTTP proxy at :8118."""
    if _detect_process("privoxy"):
        return True
    try:
        with socket.create_connection(("127.0.0.1", _PRIVOXY_PORT), timeout=1):
            return True
    except Exception:
        return False


async def _get_public_ip(client: "httpx.AsyncClient") -> str:
    try:
        r = await client.get(IP_CHECK_URL, timeout=TIMEOUT_SECS)
        return r.text.strip()
    except Exception:
        return "unknown"


async def _check_tor(client: "httpx.AsyncClient") -> bool:
    try:
        r    = await client.get(TOR_CHECK_URL, timeout=TIMEOUT_SECS)
        data = r.json()
        return bool(data.get("IsTor", False))
    except Exception:
        return False


async def run_vpn_check() -> VpnCheckResult:
    vpn_ifaces = _detect_vpn_interfaces()
    vpn_found  = len(vpn_ifaces) > 0
    ss_found   = _detect_shadowsocks()
    prv_found  = _detect_privoxy()

    tor_found = False
    public_ip = "unknown"

    if _HTTPX_AVAILABLE:
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                public_ip, tor_result = await asyncio.gather(
                    _get_public_ip(client),
                    _check_tor(client),
                )
                tor_found = tor_result
        except Exception as e:
            log.warning("VPN check network request failed: %s", e)

    # Determine best anonymity layer (priority: Tor > SS > VPN > Privoxy > clearnet)
    if tor_found:
        layer = "TOR"
    elif ss_found:
        layer = "SHADOWSOCKS"
    elif vpn_found:
        layer = "VPN"
    elif prv_found:
        layer = "PRIVOXY"
    else:
        layer = "CLEARNET"

    exposed = layer == "CLEARNET"

    warning = ""
    if exposed:
        warning = (
            "⚠ OPSEC WARNING: No anonymity layer detected (VPN / Tor / Shadowsocks / Privoxy). "
            f"Your real IP {public_ip} may be exposed to all monitored targets."
        )

    return VpnCheckResult(
        vpn_detected         = vpn_found,
        tor_detected         = tor_found,
        shadowsocks_detected = ss_found,
        privoxy_detected     = prv_found,
        public_ip            = public_ip,
        vpn_interfaces       = vpn_ifaces,
        anonymity_layer      = layer,
        exposed              = exposed,
        warning              = warning,
    )


