"""State Manager — Tracks system-wide state."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.core.state")


class StateManager:
    """Central state store for the SPARK system."""

    def __init__(self) -> None:
        self._state: dict[str, Any] = {
            "status": "initializing",
            "current_goal": None,
            "current_plan": None,
            "active_agents": [],
            "active_tasks": [],
            "authority_mode": "standard",
            "user_present": False,
            "last_interaction": 0.0,
            "system_health": "ok",
        }
        self._history: list[dict[str, Any]] = []
        self._max_history = 200

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set(self, key: str, value: Any) -> None:
        old = self._state.get(key)
        self._state[key] = value
        if old != value:
            self._history.append({
                "key": key,
                "old": old,
                "new": value,
                "ts": time.time(),
            })
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history:]
            logger.debug("State[%s]: %s -> %s", key, old, value)

    def get_all(self) -> dict[str, Any]:
        return dict(self._state)

    def snapshot(self) -> dict[str, Any]:
        return {
            "state": self.get_all(),
            "history": self._history[-20:],
        }
