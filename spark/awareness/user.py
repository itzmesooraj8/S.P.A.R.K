"""User Awareness — Tracks user presence and activity."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.awareness.user")


class UserAwareness:
    """Tracks user presence, activity, and interaction patterns."""

    def __init__(self) -> None:
        self._user_present: bool = False
        self._last_interaction: float = 0.0
        self._interaction_count: int = 0
        self._idle_threshold: float = 300.0

    def mark_interaction(self) -> None:
        self._user_present = True
        self._last_interaction = time.time()
        self._interaction_count += 1

    def check_presence(self) -> dict[str, Any]:
        idle_time = time.time() - self._last_interaction if self._last_interaction > 0 else float("inf")
        self._user_present = idle_time < self._idle_threshold
        return {
            "present": self._user_present,
            "idle_seconds": idle_time if idle_time < float("inf") else 0,
            "total_interactions": self._interaction_count,
        }

    def is_idle(self, threshold: float | None = None) -> bool:
        t = threshold or self._idle_threshold
        if self._last_interaction == 0:
            return True
        return (time.time() - self._last_interaction) > t

    def get_profile(self) -> dict[str, Any]:
        return {
            "present": self._user_present,
            "last_interaction": self._last_interaction,
            "total_interactions": self._interaction_count,
        }
