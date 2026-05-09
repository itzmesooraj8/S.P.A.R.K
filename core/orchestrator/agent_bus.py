from __future__ import annotations

from collections import defaultdict
from threading import RLock
from typing import Any, Callable

import requests

from .runtime_state import record_event, update_runtime_state


Handler = Callable[[dict[str, Any]], None]


class AgentBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)
        self._lock = RLock()

    def subscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            self._handlers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Handler) -> None:
        with self._lock:
            handlers = self._handlers.get(topic, [])
            if handler in handlers:
                handlers.remove(handler)

    def emit(self, topic: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        event = record_event(topic, payload)
        with self._lock:
            handlers = list(self._handlers.get(topic, [])) + list(self._handlers.get("*", []))

        for handler in handlers:
            try:
                handler(event)
            except Exception:
                continue

        update_runtime_state(last_route={"topic": topic, "payload": payload or {}})
        try:
            requests.post(
                "http://127.0.0.1:8000/internal/broadcast",
                json={"type": "runtime_event", "payload": event},
                timeout=0.1,
            )
        except Exception:
            pass
        return event


_BUS = AgentBus()


def get_agent_bus() -> AgentBus:
    return _BUS
