"""Base Agent — Abstract base for all specialized agents."""

from __future__ import annotations

import logging
import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from spark.core.events import EventBus, Event

logger = logging.getLogger("spark.agents.base")


class AgentStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    WAITING = "waiting"
    ERROR = "error"
    STOPPED = "stopped"


class BaseAgent(ABC):
    """Abstract base class for all SPARK agents."""

    def __init__(self, name: str, event_bus: EventBus | None = None) -> None:
        self.name = name
        self.id = uuid.uuid4().hex[:8]
        self.status = AgentStatus.IDLE
        self._event_bus = event_bus
        self._created_at = time.time()
        self._last_run: float = 0.0

    @abstractmethod
    async def run(self, **kwargs: Any) -> dict[str, Any]:
        """Execute the agent's primary function."""
        ...

    def emit(self, topic: str, payload: dict[str, Any]) -> None:
        if self._event_bus:
            self._event_bus.emit(topic, payload, source=self.name)

    def info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "id": self.id,
            "status": self.status.value,
            "created_at": self._created_at,
            "last_run": self._last_run,
        }

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} name={self.name} status={self.status.value}>"
