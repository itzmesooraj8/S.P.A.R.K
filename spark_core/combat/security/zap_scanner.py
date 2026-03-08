"""
OWASP ZAP Web Application Scanner
===================================
Wrapper around python-owasp-zap-v2.4.
Requires: pip install python-owasp-zap-v2.4
          ZAP daemon running on http://localhost:8080 (or configured URL)
"""
import asyncio
import logging
from typing import TypedDict, List, Optional

log = logging.getLogger(__name__)

try:
    from zapv2 import ZAPv2  # type: ignore
    _ZAP_OK = True
except ImportError:
    _ZAP_OK = False
    log.warning("python-owasp-zap-v2.4 not installed — ZAP scanner disabled")


class ZapAlert(TypedDict):
    alert:      str
    risk:       str   # High / Medium / Low / Informational
    confidence: str
    url:        str
    description: str
    solution:   str
    cweid:      str


async def run_zap_scan(
    target_url: str,
    zap_url: str = "http://localhost:8080",
    api_key: str = "",
    scan_type: str = "spider",   # spider | ajax | active
) -> dict:
    """
    Run a ZAP scan against target_url.
    scan_type:
      spider  — passive spider + passive scan
      ajax    — Ajax spider (needs a browser driver)
      active  — full active scan (intrusive)

    Returns {"target", "scan_type", "alerts": [...], "status"}
    """
    if not _ZAP_OK:
        return {
            "target": target_url,
            "scan_type": scan_type,
            "status": "ZAP_NOT_INSTALLED",
            "alerts": [],
            "message": "Install python-owasp-zap-v2.4 and run ZAP daemon to enable scanning.",
        }

    def _blocking_scan() -> List[ZapAlert]:
        zap = ZAPv2(apikey=api_key, proxies={"http": zap_url, "https": zap_url})

        # Open target URL
        zap.urlopen(target_url)

        # Spider
        scan_id = zap.spider.scan(target_url, apikey=api_key)
        while int(zap.spider.status(scan_id)) < 100:
            import time; time.sleep(2)

        alerts: List[ZapAlert] = []
        if scan_type == "active":
            ascan_id = zap.ascan.scan(target_url, apikey=api_key)
            while int(zap.ascan.status(ascan_id)) < 100:
                import time; time.sleep(3)

        for a in zap.core.alerts(baseurl=target_url):
            alerts.append(ZapAlert(
                alert       = a.get("alert", ""),
                risk        = a.get("risk", "Informational"),
                confidence  = a.get("confidence", "Medium"),
                url         = a.get("url", target_url),
                description = a.get("description", ""),
                solution    = a.get("solution", ""),
                cweid       = a.get("cweid", ""),
            ))
        return alerts

    try:
        loop    = asyncio.get_event_loop()
        alerts  = await loop.run_in_executor(None, _blocking_scan)
        return {
            "target":    target_url,
            "scan_type": scan_type,
            "status":    "COMPLETE",
            "alerts":    alerts,
        }
    except Exception as exc:
        log.error("ZAP scan failed: %s", exc)
        return {
            "target":    target_url,
            "scan_type": scan_type,
            "status":    "ERROR",
            "alerts":    [],
            "message":   str(exc),
        }
