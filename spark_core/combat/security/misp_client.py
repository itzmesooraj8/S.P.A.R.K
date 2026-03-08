"""
MISP Threat Intelligence Client
=================================
Connects to a MISP instance (https://www.misp-project.org/) for IOC
lookups and incident event creation.

Requires: pip install pymisp
"""
import asyncio
import logging
from typing import Optional, List

log = logging.getLogger(__name__)

try:
    from pymisp import PyMISP, MISPEvent, MISPAttribute  # type: ignore
    _MISP_OK = True
except ImportError:
    _MISP_OK = False
    log.warning("pymisp not installed — MISP client disabled")


class MispClient:
    def __init__(self, url: str, api_key: str, verify_ssl: bool = True):
        self.url        = url
        self.api_key    = api_key
        self.verify_ssl = verify_ssl
        self._misp: Optional[object] = None

    def _connect(self):
        if not _MISP_OK:
            raise RuntimeError("pymisp not installed. Run: pip install pymisp")
        if self._misp is None:
            self._misp = PyMISP(self.url, self.api_key, self.verify_ssl)
        return self._misp

    async def create_incident_event(
        self,
        title: str,
        description: str,
        tlp: str = "amber",      # white | green | amber | red
        threat_level: int = 2,   # 1=High 2=Medium 3=Low 4=Undefined
    ) -> dict:
        """Create a new MISP event for an incident."""
        def _blocking():
            misp = self._connect()
            event = MISPEvent()
            event.info       = title
            event.distribution = 0   # Your organisation only
            event.threat_level_id = threat_level
            event.analysis     = 1   # Ongoing
            comment_attr = MISPAttribute()
            comment_attr.type  = "comment"
            comment_attr.value = description
            comment_attr.comment = f"TLP:{tlp.upper()}"
            event.add_attribute(**comment_attr)
            result = misp.add_event(event, pythonify=True)
            return {"event_id": result.id, "uuid": result.uuid, "title": title}

        if not _MISP_OK:
            return {"status": "MISP_NOT_INSTALLED",
                    "message": "Install pymisp and configure MISP URL + API key."}
        try:
            return await asyncio.get_event_loop().run_in_executor(None, _blocking)
        except Exception as exc:
            log.error("MISP create_incident_event failed: %s", exc)
            return {"status": "ERROR", "message": str(exc)}

    async def search_iocs(self, value: str, limit: int = 20) -> dict:
        """Search all MISP events/attributes for a given IOC value."""
        def _blocking():
            misp = self._connect()
            results = misp.search("attributes", value=value, limit=limit, pythonify=True)
            return [
                {
                    "type":    a.type,
                    "value":   a.value,
                    "event_id": a.event_id,
                    "comment": a.comment,
                    "category": a.category,
                }
                for a in (results or [])
            ]

        if not _MISP_OK:
            return {"status": "MISP_NOT_INSTALLED", "matches": []}
        try:
            matches = await asyncio.get_event_loop().run_in_executor(None, _blocking)
            return {"query": value, "matches": matches}
        except Exception as exc:
            log.error("MISP search_iocs failed: %s", exc)
            return {"query": value, "matches": [], "error": str(exc)}
