"""
SPARK Tor Gateway — Site Verifier
==================================
Calculates a real-time trust score for a .onion address by:
  1. Checking if it exists in the vetted registry (instant high trust)
  2. Attempting an HTTP HEAD request over Tor SOCKS5 proxy (127.0.0.1:9050)
  3. Measuring response time and checking for expected headers

Requirements for live checking:
  - Tor daemon running locally (systemctl start tor / Tor Browser running)
  - httpx[socks] installed

If Tor is not running, the verifier returns registry-only results.
"""
import asyncio
import logging
from urllib.parse import urlparse
from typing import Optional

log  = logging.getLogger(__name__)

_TOR_PROXY   = "socks5://127.0.0.1:9050"
_TIMEOUT     = 30

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False


async def _check_reachability(url: str) -> dict:
    """Try to reach the onion URL via local Tor SOCKS5 proxy."""
    if not _HTTPX:
        return {"reachable": None, "reason": "httpx not available"}

    try:
        transport = httpx.AsyncHTTPTransport(proxy=_TOR_PROXY)
        async with httpx.AsyncClient(transport=transport, verify=False) as client:  # nosec
            import time
            t0 = time.monotonic()
            r  = await client.head(url, timeout=_TIMEOUT, follow_redirects=True)
            latency_ms = round((time.monotonic() - t0) * 1000)
            return {
                "reachable":   True,
                "status_code": r.status_code,
                "latency_ms":  latency_ms,
                "headers":     dict(r.headers),
            }
    except httpx.ProxyError:
        return {
            "reachable": False,
            "reason":    "Tor proxy not reachable at 127.0.0.1:9050. Is Tor running?",
        }
    except Exception as e:
        return {"reachable": False, "reason": str(e)}


def _calculate_trust_score(
    registry_entry: Optional[dict],
    reachability: dict,
) -> int:
    """Compute a 0-100 trust score from available signals."""
    score = 0
    if registry_entry:
        score += registry_entry.get("trust_score", 0)
        return score  # vetted entries use their pre-assigned score

    # Unknown site scoring
    if reachability.get("reachable"):
        score += 30                                   # reachable adds base
        status = reachability.get("status_code", 0)
        if 200 <= status < 300:
            score += 20
        elif status == 404:
            score += 5                               # up but not found
    else:
        score = max(0, score - 10)

    return min(score, 70)        # unknown sites are capped at 70


async def verify_site(url: str) -> dict:
    """Verify reachability and trust of an onion URL."""
    from .onion_registry import get_all_sites

    parsed = urlparse(url)
    if not parsed.netloc.endswith(".onion") and not parsed.path.endswith(".onion"):
        return {
            "error": "Not a .onion address",
            "url":   url,
        }

    # Check registry
    registry_entry = next(
        (s for s in get_all_sites() if url in s["url"] or s["url"] in url),
        None,
    )

    # Check live reachability
    reachability = await _check_reachability(url)

    trust_score = _calculate_trust_score(registry_entry, reachability)

    return {
        "url":             url,
        "trust_score":     trust_score,
        "in_registry":     registry_entry is not None,
        "registry_entry":  registry_entry,
        "reachability":    reachability,
        "verdict": (
            "TRUSTED"      if trust_score >= 90 else
            "LIKELY_SAFE"  if trust_score >= 70 else
            "UNKNOWN"      if trust_score >= 40 else
            "CAUTION"
        ),
    }
