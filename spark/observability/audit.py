"""Audit Logger — Compliance and security audit trail."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.observability.audit")


class AuditLogger:
    """
    Compliance and security audit trail.

    Every significant action is recorded with:
    - Who (agent/user)
    - What (action)
    - When (timestamp)
    - Result (success/failure)
    - Context (details)
    """

    def __init__(self, storage_path: str = "spark_dev_memory/audit.jsonl") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._recent: list[dict[str, Any]] = []

    def log(self, action: str, actor: str, result: str, context: dict[str, Any] | None = None, risk_level: str = "low") -> None:
        entry = {
            "action": action,
            "actor": actor,
            "result": result,
            "risk_level": risk_level,
            "context": context or {},
            "timestamp": time.time(),
        }
        self._recent.append(entry)
        if len(self._recent) > 200:
            self._recent = self._recent[-200:]

        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("Audit log failed: %s", exc)

    def log_security(self, event: str, details: dict[str, Any] | None = None) -> None:
        self.log(event, "security", "logged", details, risk_level="high")

    def log_permission(self, action: str, granted: bool, reason: str = "") -> None:
        self.log(f"permission_{action}", "authority", "granted" if granted else "denied", {"reason": reason}, risk_level="medium" if granted else "high")

    def log_data_access(self, resource: str, action: str, success: bool) -> None:
        self.log(f"data_access_{action}", "system", "success" if success else "failed", {"resource": resource})

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._recent[-limit:]

    def search(self, query: str, limit: int = 20) -> list[dict[str, Any]]:
        query_lower = query.lower()
        matches = [e for e in self._recent if query_lower in e.get("action", "").lower() or query_lower in str(e.get("context", {})).lower()]
        return matches[-limit:]
