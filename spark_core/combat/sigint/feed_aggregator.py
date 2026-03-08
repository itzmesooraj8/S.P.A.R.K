"""
SPARK SIGINT — Multi-Source Threat Feed Aggregator
====================================================
Pulls the latest threat intelligence from four public sources:

  • CISA KEV  — Known Exploited Vulnerabilities catalog (no key required)
  • NVD/CVE   — NIST National Vulnerability Database (no key required, rate-limited)
  • GreyNoise — Noise / mass-scanner context (GREYNOISE_API_KEY optional)
  • HIBP      — Data breach feed summary (HIBP_API_KEY required for full access)

All feeds are fetched concurrently with graceful degradation on failure.
"""
import asyncio
import logging
import os
from datetime import datetime, timezone
from typing import Any

log = logging.getLogger(__name__)

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False

_TIMEOUT = 20

_CISA_KEV_URL   = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
_NVD_RECENT_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"
_GREYNOISE_URL  = "https://api.greynoise.io/v3/community"


async def _fetch_cisa_kev(client: "httpx.AsyncClient") -> dict:
    try:
        r = await client.get(_CISA_KEV_URL, timeout=_TIMEOUT)
        if r.status_code == 200:
            data = r.json()
            vulns = data.get("vulnerabilities", [])
            return {
                "source":       "CISA KEV",
                "total":        data.get("count", len(vulns)),
                "catalog_version": data.get("catalogVersion"),
                "date_released": data.get("dateReleased"),
                "recent":       vulns[-20:][::-1],   # last 20, newest first
            }
        return {"source": "CISA KEV", "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"source": "CISA KEV", "error": str(e)}


async def _fetch_nvd_recent(client: "httpx.AsyncClient") -> dict:
    try:
        r = await client.get(
            _NVD_RECENT_URL,
            params={"resultsPerPage": 20, "startIndex": 0},
            headers={"Accept": "application/json"},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            data        = r.json()
            total_results = data.get("totalResults", 0)
            items       = []
            for vuln in data.get("vulnerabilities", [])[:20]:
                cve       = vuln.get("cve", {})
                cve_id    = cve.get("id")
                descs     = cve.get("descriptions", [])
                desc      = next((d["value"] for d in descs if d.get("lang") == "en"), "")
                metrics   = cve.get("metrics", {})
                cvss_v3   = metrics.get("cvssMetricV31", metrics.get("cvssMetricV30", []))
                base_score = None
                severity   = None
                if cvss_v3:
                    cvss_data  = cvss_v3[0].get("cvssData", {})
                    base_score = cvss_data.get("baseScore")
                    severity   = cvss_data.get("baseSeverity")
                items.append({
                    "cve_id":     cve_id,
                    "description": desc[:300],
                    "base_score": base_score,
                    "severity":   severity,
                    "published":  cve.get("published"),
                })
            return {
                "source":        "NVD",
                "total_results": total_results,
                "items":         items,
            }
        return {"source": "NVD", "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"source": "NVD", "error": str(e)}


async def _fetch_greynoise(client: "httpx.AsyncClient") -> dict:
    api_key = os.environ.get("GREYNOISE_API_KEY", "")
    if not api_key:
        return {
            "source":    "GreyNoise",
            "available": False,
            "reason":    "GREYNOISE_API_KEY not set in environment.",
        }
    try:
        r = await client.get(
            f"{_GREYNOISE_URL}/stats",
            headers={"key": api_key},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return {"source": "GreyNoise", "data": r.json()}
        return {"source": "GreyNoise", "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"source": "GreyNoise", "error": str(e)}


async def aggregate_feeds() -> dict:
    """Fetch all feeds concurrently and return aggregated payload."""
    if not _HTTPX:
        return {"error": "httpx not installed — cannot fetch threat feeds."}

    async with httpx.AsyncClient(follow_redirects=True) as client:
        cisa_task       = _fetch_cisa_kev(client)
        nvd_task        = _fetch_nvd_recent(client)
        greynoise_task  = _fetch_greynoise(client)

        cisa_result, nvd_result, greynoise_result = await asyncio.gather(
            cisa_task, nvd_task, greynoise_task, return_exceptions=True
        )

    def _safe(r: Any) -> Any:
        return {"error": str(r)} if isinstance(r, Exception) else r

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "feeds": {
            "cisa_kev":  _safe(cisa_result),
            "nvd":       _safe(nvd_result),
            "greynoise": _safe(greynoise_result),
        },
    }
