from __future__ import annotations

from dataclasses import asdict
from typing import Any

from .agent_bus import get_agent_bus
from .intent_engine import Intent, IntentEngine
from .runtime_state import get_runtime_snapshot, update_runtime_state
from .task_graph import TaskGraphBuilder


_AGENT_MAP = {
    "action": "system_agent",
    "research": "research_agent",
    "coding": "coding_agent",
    "vision": "vision_agent",
    "memory": "memory_agent",
    "scheduler": "scheduler_agent",
    "general": "system_agent",
}


class OrchestratorRouter:
    def __init__(self) -> None:
        self._intent_engine = IntentEngine()
        self._graph_builder = TaskGraphBuilder()
        self._bus = get_agent_bus()

    def resolve_intent(self, text: str, context: dict[str, Any] | None = None) -> Intent:
        intent = self._intent_engine.resolve(text, context)
        update_runtime_state(mode=intent.route, last_intent=asdict(intent), inference_source=intent.preferred_inference)
        self._bus.emit("intent_resolved", {"intent": asdict(intent), "context": context or {}})
        return intent

    def select_agent(self, intent: Intent) -> str:
        return _AGENT_MAP.get(intent.route, "system_agent")

    def build_graph(self, intent: Intent, context: dict[str, Any] | None = None):
        return self._graph_builder.build(intent.route, intent.name, context)

    def route(self, text: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        context = context or {}
        intent = self.resolve_intent(text, context)
        selected_agent = self.select_agent(intent)
        graph = self.build_graph(intent, context)

        route = {
            "intent": asdict(intent),
            "selected_agent": selected_agent,
            "graph": {
                "intent": graph.intent,
                "nodes": [asdict(node) for node in graph.nodes],
            },
            "runtime": get_runtime_snapshot(),
        }

        update_runtime_state(last_agent=selected_agent, last_route=route, queue_depth=max(len(graph.nodes) - 1, 0))
        self._bus.emit("route_planned", route)
        return route


_ROUTER = OrchestratorRouter()


def get_orchestrator_router() -> OrchestratorRouter:
    return _ROUTER
