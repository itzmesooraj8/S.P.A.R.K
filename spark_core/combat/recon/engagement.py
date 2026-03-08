"""
SPARK Recon Engine — Engagement Manager
========================================
Manages the full lifecycle of a penetration-testing / OSINT engagement:
  1. Create engagement  → allocates ID + log directory
  2. Log events         → writes timestamped chain-of-custody records
  3. Close engagement   → finalises the report

All engagement data is stored locally under:
  spark_dev_memory/engagements/{engagement_id}/

Chain-of-custody log format (JSONL — one JSON object per line):
  {"ts": "2024-01-01T12:00:00Z", "actor": "SPARK", "action": "...", "data": {...}}
"""
import json
import uuid
import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path

log = logging.getLogger(__name__)

_ENGAGEMENTS_DIR = (
    Path(__file__).parent.parent.parent.parent / "spark_dev_memory" / "engagements"
)


class EngagementManager:
    def __init__(self, target: str, description: str = "") -> None:
        self.engagement_id = str(uuid.uuid4())[:8].upper()
        self.target        = target
        self.description   = description
        self._dir: Path    = _ENGAGEMENTS_DIR / self.engagement_id
        self._log_path: Path = self._dir / "custody_chain.jsonl"
        self._meta_path: Path = self._dir / "meta.json"
        self._status       = "CREATED"

    async def begin(self) -> None:
        self._dir.mkdir(parents=True, exist_ok=True)
        meta = {
            "engagement_id": self.engagement_id,
            "target":        self.target,
            "description":   self.description,
            "started_at":    _now_iso(),
            "status":        "ACTIVE",
        }
        self._meta_path.write_text(json.dumps(meta, indent=2))
        await self.log_event(
            action="ENGAGEMENT_STARTED",
            data={"target": self.target, "description": self.description},
        )
        self._status = "ACTIVE"

    async def log_event(self, action: str, data: dict) -> None:
        record = {
            "ts":     _now_iso(),
            "actor":  "SPARK",
            "action": action,
            "data":   data,
        }
        with self._log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    async def close(self, summary: str = "") -> None:
        await self.log_event(
            action="ENGAGEMENT_CLOSED",
            data={"summary": summary},
        )
        if self._meta_path.exists():
            meta = json.loads(self._meta_path.read_text())
            meta["status"]    = "CLOSED"
            meta["closed_at"] = _now_iso()
            meta["summary"]   = summary
            self._meta_path.write_text(json.dumps(meta, indent=2))
        self._status = "CLOSED"

    def get_log(self) -> list[dict]:
        if not self._log_path.exists():
            return []
        records = []
        for line in self._log_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
        return records


def list_engagements() -> list[dict]:
    """Return metadata for all engagements on disk."""
    _ENGAGEMENTS_DIR.mkdir(parents=True, exist_ok=True)
    results = []
    for eng_dir in sorted(_ENGAGEMENTS_DIR.iterdir(), reverse=True):
        meta_path = eng_dir / "meta.json"
        if meta_path.exists():
            try:
                results.append(json.loads(meta_path.read_text()))
            except Exception:
                pass
    return results


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
