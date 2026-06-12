"""Reflection Agent — Self-evaluation and learning."""

from __future__ import annotations

import logging
import time
from typing import Any

from spark.agents.base import BaseAgent, AgentStatus
from spark.cognition.reflection import ReflectionEngine

logger = logging.getLogger("spark.agents.reflection")


class ReflectionAgent(BaseAgent):
    """Performs self-reflection and learns from actions."""

    def __init__(self, event_bus=None):
        super().__init__("reflection", event_bus)
        self.reflection_engine = ReflectionEngine()

    async def run(self, recent_actions: list[dict[str, Any]] | None = None, **kwargs) -> dict[str, Any]:
        self.status = AgentStatus.RUNNING
        self.emit("reflection.start", {})

        try:
            actions = recent_actions or []
            reflection = self.reflection_engine.reflect(actions, kwargs.get("context"))
            self.status = AgentStatus.IDLE
            self._last_run = time.time()
            self.emit("reflection.complete", reflection)
            return reflection
        except Exception as exc:
            self.status = AgentStatus.ERROR
            return {"error": str(exc)}

    def should_reflect(self) -> bool:
        return self.reflection_engine.should_reflect()

    def recent_reflections(self, limit: int = 10) -> list[dict[str, Any]]:
        return self.reflection_engine.recent(limit)
