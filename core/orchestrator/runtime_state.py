from __future__ import annotations

from dataclasses import dataclass, field, asdict
from threading import RLock
from time import time
from typing import Any


@dataclass
class RuntimeState:
    mode: str = "idle"
    last_intent: dict[str, Any] = field(default_factory=dict)
    last_agent: str = ""
    last_route: dict[str, Any] = field(default_factory=dict)
    active_tasks: list[dict[str, Any]] = field(default_factory=list)
    last_events: list[dict[str, Any]] = field(default_factory=list)
    inference_source: str = "ollama"
    memory_hits: int = 0
    retrievals: int = 0
    queue_depth: int = 0
    updated_at: float = field(default_factory=time)


_STATE = RuntimeState()
_LOCK = RLock()


def get_runtime_state() -> RuntimeState:
    return _STATE


def update_runtime_state(**changes: Any) -> RuntimeState:
    with _LOCK:
        for key, value in changes.items():
            if hasattr(_STATE, key):
                setattr(_STATE, key, value)
        _STATE.updated_at = time()
        return _STATE


def record_event(event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    event = {
        "type": event_type,
        "payload": payload or {},
        "ts": time(),
    }
    with _LOCK:
        _STATE.last_events = (_STATE.last_events + [event])[-25:]
        _STATE.updated_at = event["ts"]
    return event


def get_runtime_snapshot() -> dict[str, Any]:
    with _LOCK:
        return asdict(_STATE)
