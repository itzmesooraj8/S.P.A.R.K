from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TaskNode:
    id: str
    agent: str
    action: str
    requires_confirmation: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TaskGraph:
    intent: str
    nodes: list[TaskNode] = field(default_factory=list)


class TaskGraphBuilder:
    def build(self, route: str, intent_name: str, context: dict[str, Any] | None = None) -> TaskGraph:
        context = context or {}
        nodes: list[TaskNode] = []

        if route == "action":
            nodes.extend([
                TaskNode("intent", "system_agent", "validate_intent", metadata={"intent": intent_name}),
                TaskNode("execute", "system_agent", "execute_action", requires_confirmation=context.get("requires_confirmation", False), metadata=context),
                TaskNode("persist", "memory_agent", "record_outcome", metadata={"source": "orchestrator"}),
            ])
        elif route == "research":
            nodes.extend([
                TaskNode("retrieve", "memory_agent", "pull_relevant_memory", metadata=context),
                TaskNode("research", "research_agent", "search_and_summarize", metadata=context),
                TaskNode("persist", "memory_agent", "store_summary", metadata={"source": "orchestrator"}),
            ])
        elif route == "coding":
            nodes.extend([
                TaskNode("retrieve", "memory_agent", "pull_project_context", metadata=context),
                TaskNode("code", "coding_agent", "analyze_or_generate", metadata=context),
                TaskNode("persist", "memory_agent", "store_solution", metadata={"source": "orchestrator"}),
            ])
        elif route == "vision":
            nodes.extend([
                TaskNode("capture", "vision_agent", "capture_visual_context", metadata=context),
                TaskNode("analyze", "vision_agent", "analyze_screen", metadata=context),
                TaskNode("persist", "memory_agent", "store_visual_notes", metadata={"source": "orchestrator"}),
            ])
        elif route == "memory":
            nodes.extend([
                TaskNode("retrieve", "memory_agent", "semantic_recall", metadata=context),
                TaskNode("respond", "memory_agent", "compose_recall_response", metadata=context),
            ])
        elif route == "scheduler":
            nodes.extend([
                TaskNode("plan", "scheduler_agent", "build_schedule", metadata=context),
                TaskNode("persist", "memory_agent", "store_schedule", metadata={"source": "orchestrator"}),
            ])
        else:
            nodes.extend([
                TaskNode("respond", "system_agent", "compose_response", metadata=context),
                TaskNode("persist", "memory_agent", "store_conversation", metadata={"source": "orchestrator"}),
            ])

        return TaskGraph(intent=intent_name, nodes=nodes)
