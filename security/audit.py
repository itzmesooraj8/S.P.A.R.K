from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


AUDIT_LOG = Path("spark_dev_memory/security_audit.jsonl")
AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)


def record_audit(event: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    entry = {
        "timestamp": time.time(),
        "event": event,
        "payload": payload or {},
    }
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def get_recent_audit(limit: int = 50) -> list[dict[str, Any]]:
    if not AUDIT_LOG.exists():
        return []

    items: list[dict[str, Any]] = []
    for line in AUDIT_LOG.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        try:
            items.append(json.loads(stripped))
        except json.JSONDecodeError:
            continue
    return items[-max(limit, 1):]
