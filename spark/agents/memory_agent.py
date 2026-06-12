"""Memory Agent — Manages memory operations."""

from __future__ import annotations

import logging
import time
from typing import Any

from spark.agents.base import BaseAgent, AgentStatus
from spark.memory.semantic import SemanticMemory, MemoryType
from spark.memory.episodic import EpisodicMemory
from spark.memory.procedural import ProceduralMemory

logger = logging.getLogger("spark.agents.memory_agent")


class MemoryAgent(BaseAgent):
    """Manages all memory operations."""

    def __init__(self, event_bus=None):
        super().__init__("memory", event_bus)
        self.semantic = SemanticMemory()
        self.episodic = EpisodicMemory()
        self.procedural = ProceduralMemory()

    async def run(self, action: str, **kwargs) -> dict[str, Any]:
        self.status = AgentStatus.RUNNING

        try:
            if action == "remember":
                return self._remember(kwargs)
            elif action == "recall":
                return self._recall(kwargs)
            elif action == "record":
                return self._record(kwargs)
            elif action == "stats":
                return self._stats()
            else:
                return {"error": f"Unknown action: {action}"}
        finally:
            self.status = AgentStatus.IDLE
            self._last_run = time.time()

    def _remember(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        text = kwargs.get("text", "")
        mem_type = kwargs.get("type", "fact")
        mt = MemoryType(mem_type) if mem_type in [e.value for e in MemoryType] else MemoryType.FACT
        doc_id = self.semantic.store(text, mt, kwargs.get("metadata"))
        return {"stored": True, "id": doc_id, "type": mem_type}

    def _recall(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        query = kwargs.get("query", "")
        results = self.semantic.recall(query, kwargs.get("top_k", 5))
        return {"results": results, "count": len(results)}

    def _record(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        role = kwargs.get("role", "user")
        content = kwargs.get("content", "")
        self.episodic.record(role, content, kwargs.get("metadata"))
        return {"recorded": True}

    def _stats(self) -> dict[str, Any]:
        return {
            "semantic_count": self.semantic.count(),
            "episodic_count": self.episodic.count(),
            "procedures": self.procedural.list_all(),
        }

    def extract_and_store(self, text: str) -> list[str]:
        return self.semantic.extract_facts(text)
