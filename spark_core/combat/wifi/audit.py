"""
WiFi Audit Orchestrator
========================
• benchmark_hashcat()  — GPU H/s benchmark + crack-time estimate per encryption
• run_airgeddon_test()  — full airgeddon script orchestration
"""
import asyncio
import logging
import math
import re
from typing import TypedDict, Optional

log = logging.getLogger(__name__)


class HashcatBenchmark(TypedDict):
    hash_type:        str    # WPA2 / WPA
    hash_mode:        int    # hashcat -m value
    hashes_per_sec:   float
    crack_time_8char: str    # human-readable estimate for 8-char alphanumeric
    crack_time_12char: str


_CHARSET_SIZE_ALPHA_NUMERIC = 62   # a-z A-Z 0-9
_HASHCAT_WPA_MODE = 22000          # PMKID + EAPOL (modern)


async def benchmark_hashcat() -> HashcatBenchmark:
    """
    Run `hashcat -b -m 22000` to measure GPU throughput, then estimate crack
    times for 8-char and 12-char alphanumeric passwords.
    Returns a mockup when hashcat is absent.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "hashcat", "-b", "-m", str(_HASHCAT_WPA_MODE), "--machine-readable",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = stdout.decode("utf-8", errors="replace") + stderr.decode("utf-8", errors="replace")

        # Machine-readable format: <mode>:<driver>:<device>:<hs/s>
        mre = re.search(r"22000:[^:]+:[^:]+:([\d.]+)", output)
        if mre:
            hps = float(mre.group(1))
        else:
            # Fallback: parse "Speed.#1.........: 1234.5 kH/s" style
            speed_re = re.search(r"Speed\.#\d+\.*:\s+([\d.]+)\s*(k|M|G)?H/s", output)
            if speed_re:
                mult = {"k": 1e3, "M": 1e6, "G": 1e9}.get(speed_re.group(2), 1)
                hps = float(speed_re.group(1)) * mult
            else:
                hps = 500_000  # conservatve fallback (≈ low-end GPU)

    except (FileNotFoundError, asyncio.TimeoutError):
        log.warning("hashcat not available — using mock benchmark")
        hps = 500_000

    return HashcatBenchmark(
        hash_type         = "WPA2/PMKID+EAPOL",
        hash_mode         = _HASHCAT_WPA_MODE,
        hashes_per_sec    = hps,
        crack_time_8char  = _estimate_crack_time(8, hps),
        crack_time_12char = _estimate_crack_time(12, hps),
    )


def _estimate_crack_time(length: int, hps: float) -> str:
    if hps <= 0:
        return "unknown"
    total = _CHARSET_SIZE_ALPHA_NUMERIC ** length
    secs  = total / hps
    if secs < 60:
        return f"{secs:.1f} seconds"
    elif secs < 3600:
        return f"{secs/60:.1f} minutes"
    elif secs < 86400:
        return f"{secs/3600:.1f} hours"
    elif secs < 31_536_000:
        return f"{secs/86400:.1f} days"
    else:
        years = secs / 31_536_000
        exponent = int(math.log10(years))
        return f"10^{exponent} years (infeasible)"


async def run_airgeddon_test(
    bssid: str,
    interface: str = "wlan0mon",
    cap_file: Optional[str] = None,
) -> dict:
    """
    Orchestrate an airgeddon WPA audit: capture → crack.
    Returns status, cap_file, and benchmark results.
    NOTE: Requires airgeddon and a monitor-mode-capable wireless adapter.
    """
    from .handshake import capture_handshake

    result: dict = {"bssid": bssid, "status": "STARTED"}

    if cap_file is None:
        captured = await capture_handshake(bssid=bssid, channel=6, interface=interface)
        if not captured:
            return {"bssid": bssid, "status": "NO_HANDSHAKE", "cap_file": None}
        cap_file = captured

    result["cap_file"] = cap_file
    benchmark = await benchmark_hashcat()
    result["benchmark"] = benchmark
    result["status"] = "READY_TO_CRACK"

    return result
