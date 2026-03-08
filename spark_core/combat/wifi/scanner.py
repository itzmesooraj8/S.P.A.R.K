"""
WiFi Network Scanner
====================
Wraps airodump-ng / iw / netsh (platform-adaptive) to enumerate nearby
wireless networks.  Falls back to a mock list when wireless tooling is absent,
so the frontend can always render something useful.
"""
import re
import sys
import json
import asyncio
import subprocess
import logging
from typing import TypedDict, List

log = logging.getLogger(__name__)


class WifiNetwork(TypedDict):
    bssid:       str
    ssid:        str
    channel:     int
    signal_dbm:  int
    encryption:  str   # OPEN | WEP | WPA | WPA2 | WPA3
    clients:     int
    handshake:   bool  # has a captured handshake on disk


def _parse_iw_output(raw: str) -> List[WifiNetwork]:
    networks: List[WifiNetwork] = []
    current: dict = {}

    bssid_re  = re.compile(r"BSS ([0-9a-f:]{17})", re.I)
    ssid_re   = re.compile(r"SSID: (.+)")
    signal_re = re.compile(r"signal: ([-\d.]+) dBm")
    chan_re   = re.compile(r"DS Parameter set: channel (\d+)")
    enc_re    = re.compile(r"(WPA3|WPA2|WPA|WEP|RSN)", re.I)

    for line in raw.splitlines():
        bm = bssid_re.search(line)
        if bm:
            if current.get("bssid"):
                networks.append(_finalise(current))
            current = {"bssid": bm.group(1).upper(), "ssid": "", "channel": 0,
                       "signal_dbm": -100, "encryption": "OPEN", "clients": 0, "handshake": False}
        sm = ssid_re.search(line)
        if sm and current:
            current["ssid"] = sm.group(1).strip()
        sg = signal_re.search(line)
        if sg and current:
            current["signal_dbm"] = int(float(sg.group(1)))
        ch = chan_re.search(line)
        if ch and current:
            current["channel"] = int(ch.group(1))
        em = enc_re.search(line)
        if em and current:
            current["encryption"] = em.group(1).upper()

    if current.get("bssid"):
        networks.append(_finalise(current))
    return networks


def _finalise(d: dict) -> WifiNetwork:
    return WifiNetwork(
        bssid      = d.get("bssid", "00:00:00:00:00:00"),
        ssid       = d.get("ssid", "<hidden>"),
        channel    = d.get("channel", 0),
        signal_dbm = d.get("signal_dbm", -100),
        encryption = d.get("encryption", "OPEN"),
        clients    = d.get("clients", 0),
        handshake  = d.get("handshake", False),
    )


def _parse_netsh_output(raw: str) -> List[WifiNetwork]:
    networks: List[WifiNetwork] = []
    current: dict = {}

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("SSID") and ":" in line and "BSSID" not in line:
            if current:
                networks.append(_finalise(current))
            current = {"bssid": "00:00:00:00:00:00", "ssid": line.split(":", 1)[1].strip(),
                       "channel": 0, "signal_dbm": -100, "encryption": "OPEN",
                       "clients": 0, "handshake": False}
        elif "BSSID" in line and ":" in line:
            parts = line.split(":", 1)
            if len(parts) == 2:
                current["bssid"] = parts[1].strip().upper()
        elif "Signal" in line and ":" in line:
            try:
                pct = int(line.split(":")[1].strip().replace("%", ""))
                current["signal_dbm"] = -100 + int(pct / 2)
            except ValueError:
                pass
        elif "Channel" in line and ":" in line:
            try:
                current["channel"] = int(line.split(":")[1].strip())
            except ValueError:
                pass
        elif "Authentication" in line and ":" in line:
            auth = line.split(":", 1)[1].strip().upper()
            if "WPA3" in auth:
                current["encryption"] = "WPA3"
            elif "WPA2" in auth:
                current["encryption"] = "WPA2"
            elif "WPA" in auth:
                current["encryption"] = "WPA"
            elif "WEP" in auth:
                current["encryption"] = "WEP"
            else:
                current["encryption"] = "OPEN"

    if current:
        networks.append(_finalise(current))
    return networks


async def scan_wifi(interface: str = "wlan0") -> List[WifiNetwork]:
    """
    Enumerate nearby WiFi networks.
    Uses: iw dev scan (Linux), netsh wlan show networks (Windows), or mock fallback.
    """
    networks: List[WifiNetwork] = []
    try:
        if sys.platform == "win32":
            result = await asyncio.create_subprocess_exec(
                "netsh", "wlan", "show", "networks", "mode=Bssid",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=15)
            networks = _parse_netsh_output(stdout.decode("utf-8", errors="replace"))
        else:
            result = await asyncio.create_subprocess_exec(
                "iw", "dev", interface, "scan",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(result.communicate(), timeout=20)
            networks = _parse_iw_output(stdout.decode("utf-8", errors="replace"))
    except (FileNotFoundError, asyncio.TimeoutError) as exc:
        log.warning("WiFi scan failed (%s), returning mock data", exc)
        networks = _mock_networks()
    except Exception as exc:
        log.error("WiFi scan error: %s", exc)
        networks = _mock_networks()

    return networks


def _mock_networks() -> List[WifiNetwork]:
    """Deterministic mock for environments without wireless tooling."""
    return [
        WifiNetwork(bssid="AA:BB:CC:DD:EE:01", ssid="SPARK-TEST-AP1", channel=6,
                    signal_dbm=-55, encryption="WPA2", clients=3, handshake=False),
        WifiNetwork(bssid="AA:BB:CC:DD:EE:02", ssid="OPEN-GUEST", channel=11,
                    signal_dbm=-72, encryption="OPEN", clients=1, handshake=False),
        WifiNetwork(bssid="AA:BB:CC:DD:EE:03", ssid="SecureNet-5G", channel=36,
                    signal_dbm=-48, encryption="WPA3", clients=0, handshake=False),
    ]
