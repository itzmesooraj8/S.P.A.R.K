"""Chat Channel — Text-based communication."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.communication.chat")


class ChatChannel:
    """Handles text-based chat communication."""

    def __init__(self) -> None:
        self._history: list[dict[str, Any]] = []

    def send(self, message: str, role: str = "assistant") -> dict[str, Any]:
        entry = {
            "role": role,
            "content": message,
            "timestamp": time.time(),
        }
        self._history.append(entry)
        return entry

    def receive(self, message: str, role: str = "user") -> dict[str, Any]:
        entry = {
            "role": role,
            "content": message,
            "timestamp": time.time(),
        }
        self._history.append(entry)
        return entry

    def history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self._history[-limit:]

    def clear(self) -> None:
        self._history.clear()
