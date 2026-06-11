"""Durable security audit trail for S.P.A.R.K. runtime events."""

from __future__ import annotations

import json
import logging
import os
import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

logger = logging.getLogger("SPARK_AUDIT")

DEFAULT_AUDIT_LOG = Path("spark_dev_memory/security_audit.jsonl")
SENSITIVE_KEYS = {
    "access_token",
    "authorization",
    "bootstrap_token",
    "password",
    "refresh_token",
    "secret",
    "signature",
    "token",
}


def _audit_path() -> Path:
    return Path(os.getenv("SPARK_SECURITY_AUDIT_LOG", str(DEFAULT_AUDIT_LOG)))


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            normalized_key = str(key).lower()
            if any(sensitive in normalized_key for sensitive in SENSITIVE_KEYS):
                redacted[str(key)] = "[redacted]"
            else:
                redacted[str(key)] = _redact(item)
        return redacted
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, tuple):
        return [_redact(item) for item in value]
    return value


def record_audit(event_type: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    event = {
        "id": uuid.uuid4().hex,
        "timestamp": time.time(),
        "event": str(event_type or "unknown"),
        "payload": _redact(dict(payload or {})),
    }

    path = _audit_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, default=str))
            handle.write("\n")
    except Exception as exc:
        logger.error("Failed to record security audit event %s: %s", event["event"], exc)

    return event


def get_recent_audit(limit: int = 25) -> list[dict[str, Any]]:
    try:
        limit = max(0, min(int(limit), 500))
    except Exception:
        limit = 25
    if limit == 0:
        return []

    path = _audit_path()
    if not path.exists():
        return []

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception as exc:
        logger.error("Failed reading security audit log: %s", exc)
        return []

    events: list[dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events
