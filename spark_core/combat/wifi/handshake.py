"""
WiFi Handshake Capture
======================
Wraps airodump-ng to capture WPA/WPA2 handshakes for offline auditing.
Requires root / admin privileges and a wireless card in monitor mode.
"""
import asyncio
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

CAPTURES_DIR = Path(__file__).parent / "captures"
CAPTURES_DIR.mkdir(exist_ok=True)


async def capture_handshake(
    bssid: str,
    channel: int,
    interface: str = "wlan0mon",
    duration_secs: int = 60,
) -> Optional[str]:
    """
    Run airodump-ng against a specific BSSID/channel and attempt to capture
    a PMKID or 4-way handshake.

    Returns the path of the .cap file on success, or None if capture failed.
    """
    safe_bssid = bssid.replace(":", "-")
    cap_prefix = str(CAPTURES_DIR / f"hs_{safe_bssid}")

    cmd = [
        "airodump-ng",
        "--bssid", bssid,
        "--channel", str(channel),
        "--write", cap_prefix,
        "--output-format", "pcap",
        "--write-interval", "1",
        interface,
    ]
    log.info("Starting handshake capture: %s (duration=%ds)", bssid, duration_secs)

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )
        await asyncio.wait_for(proc.wait(), timeout=duration_secs + 5)
    except asyncio.TimeoutError:
        # Expected — capture runs for `duration_secs` then we kill it
        try:
            proc.kill()
        except Exception:
            pass
    except FileNotFoundError:
        log.warning("airodump-ng not found — cannot capture handshake without aircrack-ng suite")
        return None
    except Exception as exc:
        log.error("Handshake capture error: %s", exc)
        return None

    cap_path = cap_prefix + "-01.cap"
    if os.path.exists(cap_path) and os.path.getsize(cap_path) > 24:  # >24 bytes = not empty pcap
        log.info("Handshake capture saved: %s", cap_path)
        return cap_path

    log.warning("No handshake captured for %s (cap file missing or empty)", bssid)
    return None
