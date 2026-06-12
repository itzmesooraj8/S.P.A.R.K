"""Goal Engine — Pursues objectives autonomously with long-term hierarchy.

Goal → Plan → Subtasks → Execution → Observation → Correction

Supports:
- Long-term goals that span days/weeks
- Goal hierarchy (goals containing subgoals)
- Goal persistence across sessions
- Adaptive planning based on reflection
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.cognition.goals")


class GoalStatus(str, Enum):
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    CORRECTING = "correcting"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    PAUSED = "paused"


class GoalPriority(int, Enum):
    CRITICAL = 10
    HIGH = 7
    MEDIUM = 5
    LOW = 3
    BACKGROUND = 1


class SubtaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class Subtask:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    tool_needed: str | None = None
    args: dict[str, Any] = field(default_factory=dict)
    status: SubtaskStatus = SubtaskStatus.PENDING
    result: str | None = None
    depends_on: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries


@dataclass
class Plan:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    goal_id: str = ""
    steps: list[Subtask] = field(default_factory=list)
    current_step: int = 0
    created_at: float = field(default_factory=time.time)
    adaptive_notes: list[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        return all(s.status in (SubtaskStatus.DONE, SubtaskStatus.SKIPPED) for s in self.steps)

    @property
    def current_subtask(self) -> Subtask | None:
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None

    @property
    def progress(self) -> float:
        if not self.steps:
            return 0.0
        done = sum(1 for s in self.steps if s.status in (SubtaskStatus.DONE, SubtaskStatus.SKIPPPED))
        return done / len(self.steps)

    def advance(self) -> bool:
        if self.current_step < len(self.steps):
            current = self.steps[self.current_step]
            if current.status in (SubtaskStatus.DONE, SubtaskStatus.FAILED, SubtaskStatus.SKIPPED):
                self.current_step += 1
                return self.current_step < len(self.steps)
        return False

    def add_adaptive_note(self, note: str) -> None:
        self.adaptive_notes.append(f"[{time.strftime('%H:%M:%S')}] {note}")


@dataclass
class Goal:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    description: str = ""
    priority: int = GoalPriority.MEDIUM
    status: GoalStatus = GoalStatus.PENDING
    plan: Plan | None = None
    parent_id: str | None = None
    child_ids: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    deadline: float | None = None
    recurrence: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    learning_tags: list[str] = field(default_factory=list)

    @property
    def is_long_term(self) -> bool:
        return self.deadline is not None and (self.deadline - self.created_at) > 86400

    @property
    def depth(self) -> int:
        return 0 if not self.parent_id else 1


class GoalEngine:
    """Manages goals with long-term hierarchy and persistence."""

    def __init__(self, storage_path: str = "spark_dev_memory/goals.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._goals: dict[str, Goal] = {}
        self._completed: list[Goal] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for g_data in data.get("active", []):
                    goal = Goal(
                        id=g_data["id"],
                        description=g_data.get("description", ""),
                        priority=g_data.get("priority", 5),
                        status=GoalStatus(g_data.get("status", "pending")),
                        parent_id=g_data.get("parent_id"),
                        child_ids=g_data.get("child_ids", []),
                        created_at=g_data.get("created_at", 0),
                        updated_at=g_data.get("updated_at", 0),
                        deadline=g_data.get("deadline"),
                        metadata=g_data.get("metadata", {}),
                    )
                    self._goals[goal.id] = goal
            except Exception as exc:
                logger.warning("Goal load failed: %s", exc)

    def _save(self) -> None:
        data = {
            "active": [
                {
                    "id": g.id,
                    "description": g.description,
                    "priority": g.priority,
                    "status": g.status.value,
                    "parent_id": g.parent_id,
                    "child_ids": g.child_ids,
                    "created_at": g.created_at,
                    "updated_at": g.updated_at,
                    "deadline": g.deadline,
                    "metadata": g.metadata,
                }
                for g in self._goals.values()
            ]
        }
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def create_goal(self, description: str, priority: int = 5, parent_id: str | None = None, deadline: float | None = None, metadata: dict[str, Any] | None = None) -> Goal:
        goal = Goal(
            description=description,
            priority=priority,
            parent_id=parent_id,
            deadline=deadline,
            metadata=metadata or {},
        )
        self._goals[goal.id] = goal
        if parent_id and parent_id in self._goals:
            self._goals[parent_id].child_ids.append(goal.id)
        self._save()
        logger.info("Goal created: [%s] %s (priority=%d)", goal.id, description, priority)
        return goal

    def create_long_term_goal(self, description: str, subgoals: list[str], deadline_days: int = 30, priority: int = 7) -> Goal:
        main_goal = self.create_goal(description, priority=priority, deadline=time.time() + (deadline_days * 86400))
        for sub_desc in subgoals:
            self.create_goal(sub_desc, priority=priority - 1, parent_id=main_goal.id)
        return main_goal

    def get_goal(self, goal_id: str) -> Goal | None:
        return self._goals.get(goal_id)

    def active_goals(self) -> list[Goal]:
        return [g for g in self._goals.values() if g.status not in (GoalStatus.COMPLETED, GoalStatus.FAILED, GoalStatus.ABANDONED)]

    def root_goals(self) -> list[Goal]:
        return [g for g in self.active_goals() if g.parent_id is None]

    def child_goals(self, parent_id: str) -> list[Goal]:
        return [g for g in self.active_goals() if g.parent_id == parent_id]

    def next_action(self) -> tuple[Goal, Subtask] | None:
        priorities = sorted(self.active_goals(), key=lambda g: g.priority, reverse=True)
        for goal in priorities:
            if goal.plan and goal.plan.current_subtask:
                subtask = goal.plan.current_subtask
                if subtask.status == SubtaskStatus.PENDING:
                    return goal, subtask
            if not goal.plan:
                return goal, Subtask(description=f"Plan needed for: {goal.description}")
        return None

    def complete_subtask(self, goal_id: str, subtask_id: str, result: str, success: bool = True) -> None:
        goal = self._goals.get(goal_id)
        if not goal or not goal.plan:
            return
        for subtask in goal.plan.steps:
            if subtask.id == subtask_id:
                subtask.status = SubtaskStatus.DONE if success else SubtaskStatus.FAILED
                subtask.result = result
                if not success and subtask.can_retry():
                    subtask.retry_count += 1
                    subtask.status = SubtaskStatus.PENDING
                    goal.plan.add_adaptive_note(f"Retrying step {subtask.name} (attempt {subtask.retry_count})")
                break
        goal.updated_at = time.time()

        if goal.plan.is_complete:
            goal.status = GoalStatus.COMPLETED
            self._completed.append(goal)
            del self._goals[goal_id]
            self._check_parent_completion(goal.parent_id)
            logger.info("Goal completed: [%s] %s", goal_id, goal.description)

        self._save()

    def _check_parent_completion(self, parent_id: str | None) -> None:
        if not parent_id:
            return
        parent = self._goals.get(parent_id)
        if not parent:
            return
        children = [self._goals.get(cid) for cid in parent.child_ids]
        children = [c for c in children if c is not None]
        if all(c.status == GoalStatus.COMPLETED for c in children):
            parent.status = GoalStatus.COMPLETED
            self._completed.append(parent)
            del self._goals[parent_id]
            logger.info("Parent goal completed: [%s] %s", parent_id, parent.description)

    def adapt_plan(self, goal_id: str, reflection: dict[str, Any]) -> None:
        goal = self._goals.get(goal_id)
        if not goal or not goal.plan:
            return
        insights = reflection.get("insights", [])
        for insight in insights:
            if insight.get("type") == "pattern":
                goal.plan.add_adaptive_note(f"Adapted based on: {insight.get('description', '')}")
        goal.updated_at = time.time()
        self._save()

    def abandon_goal(self, goal_id: str, reason: str = "") -> None:
        goal = self._goals.get(goal_id)
        if goal:
            goal.status = GoalStatus.ABANDONED
            goal.updated_at = time.time()
            self._save()
            logger.info("Goal abandoned: [%s] %s (reason: %s)", goal_id, goal.description, reason)

    def stats(self) -> dict[str, Any]:
        active = self.active_goals()
        return {
            "active": len(active),
            "completed": len(self._completed),
            "root_goals": len(self.root_goals()),
            "goals": [
                {
                    "id": g.id,
                    "desc": g.description,
                    "status": g.status.value,
                    "priority": g.priority,
                    "is_long_term": g.is_long_term,
                    "children": len(g.child_ids),
                }
                for g in active
            ],
        }

    def goal_tree(self, goal_id: str) -> dict[str, Any] | None:
        goal = self._goals.get(goal_id)
        if not goal:
            return None
        tree = {
            "id": goal.id,
            "description": goal.description,
            "status": goal.status.value,
            "children": [],
        }
        for child_id in goal.child_ids:
            child_tree = self.goal_tree(child_id)
            if child_tree:
                tree["children"].append(child_tree)
        return tree
