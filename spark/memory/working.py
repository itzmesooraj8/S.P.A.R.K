"""Working Memory — Current context, objective, task, conversation.

This is what Tony Stark JARVIS depends heavily on.
Lives separately from long-term memory (semantic/episodic/procedural).
Resets per-session but persists across turns within a session.
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.memory.working")


class WorkingMemory:
    """
    Active working memory — what SPARK is currently focused on.

    Holds:
    - Current Context (what's happening right now)
    - Current Objective (what the user is trying to achieve)
    - Current Task (the immediate action being performed)
    - Current Conversation (recent exchange buffer)
    - Active Attention (what SPARK is paying attention to)
    """

    def __init__(self) -> None:
        self._context: dict[str, Any] = {
            "current_window": "",
            "current_app": "",
            "current_activity": "",
            "time_of_day": "",
            "user_mood": "neutral",
            "session_start": time.time(),
        }
        self._objective: dict[str, Any] = {
            "description": "",
            "started_at": 0.0,
            "subtasks_done": 0,
            "subtasks_total": 0,
        }
        self._task: dict[str, Any] = {
            "description": "",
            "tool_in_use": "",
            "status": "idle",
            "started_at": 0.0,
        }
        self._conversation: list[dict[str, Any]] = []
        self._max_conversation = 20
        self._attention: dict[str, Any] = {
            "focus": "",
            "priority": 0,
            "distractions": [],
        }
        self._updates: list[dict[str, Any]] = []

    def update_context(self, **kwargs: Any) -> None:
        old = dict(self._context)
        self._context.update(kwargs)
        self._log_update("context", old, self._context)

    def set_objective(self, description: str, subtasks_total: int = 0) -> None:
        self._objective = {
            "description": description,
            "started_at": time.time(),
            "subtasks_done": 0,
            "subtasks_total": subtasks_total,
        }
        self._log_update("objective", {}, self._objective)
        logger.info("Objective set: %s", description)

    def clear_objective(self) -> None:
        self._objective = {"description": "", "started_at": 0.0, "subtasks_done": 0, "subtasks_total": 0}

    def set_task(self, description: str, tool: str = "", status: str = "running") -> None:
        self._task = {
            "description": description,
            "tool_in_use": tool,
            "status": status,
            "started_at": time.time(),
        }
        self._log_update("task", {}, self._task)

    def complete_task(self, success: bool = True) -> None:
        self._task["status"] = "completed" if success else "failed"
        if self._objective["description"]:
            self._objective["subtasks_done"] += 1

    def push_conversation(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        entry = {"role": role, "content": content, "ts": time.time(), "metadata": metadata or {}}
        self._conversation.append(entry)
        if len(self._conversation) > self._max_conversation:
            self._conversation = self._conversation[-self._max_conversation:]

    def set_attention(self, focus: str, priority: int = 5) -> None:
        self._attention = {"focus": focus, "priority": priority, "distractions": []}

    def get_context(self) -> dict[str, Any]:
        return dict(self._context)

    def get_objective(self) -> dict[str, Any]:
        return dict(self._objective)

    def get_task(self) -> dict[str, Any]:
        return dict(self._task)

    def get_conversation(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._conversation[-limit:]

    def get_attention(self) -> dict[str, Any]:
        return dict(self._attention)

    def snapshot(self) -> dict[str, Any]:
        return {
            "context": self.get_context(),
            "objective": self.get_objective(),
            "task": self.get_task(),
            "attention": self.get_attention(),
            "conversation_length": len(self._conversation),
            "recent_updates": self._updates[-10:],
        }

    def is_idle(self) -> bool:
        return self._task["status"] == "idle"

    def has_objective(self) -> bool:
        return bool(self._objective["description"])

    def _log_update(self, area: str, old: dict, new: dict) -> None:
        self._updates.append({"area": area, "ts": time.time()})
        if len(self._updates) > 100:
            self._updates = self._updates[-100:]
