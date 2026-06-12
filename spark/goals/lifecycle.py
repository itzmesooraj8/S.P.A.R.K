"""Life Goal Manager — Persistent goals tracked over months/years."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.goals.lifecycle")


class LifeGoal:
    def __init__(self, description: str, category: str = "general", deadline: float | None = None, priority: int = 5):
        self.description = description
        self.category = category
        self.deadline = deadline
        self.priority = priority
        self.progress = 0.0
        self.milestones: list[dict[str, Any]] = []
        self.actions_taken: list[dict[str, Any]] = []
        self.outcomes: list[dict[str, Any]] = []
        self.status = "active"
        self.created_at = time.time()
        self.updated_at = time.time()
        self.completed_at: float | None = None

    def add_milestone(self, description: str, completed: bool = False) -> None:
        self.milestones.append({
            "description": description,
            "completed": completed,
            "created_at": time.time(),
            "completed_at": time.time() if completed else None,
        })
        self._update_progress()
        self.updated_at = time.time()

    def record_action(self, action: str, result: str, success: bool) -> None:
        self.actions_taken.append({
            "action": action,
            "result": result,
            "success": success,
            "timestamp": time.time(),
        })
        self.updated_at = time.time()

    def record_outcome(self, outcome: str, metric: float | None = None) -> None:
        self.outcomes.append({
            "outcome": outcome,
            "metric": metric,
            "timestamp": time.time(),
        })
        self.updated_at = time.time()

    def _update_progress(self) -> None:
        if not self.milestones:
            self.progress = 0.0
            return
        completed = sum(1 for m in self.milestones if m.get("completed"))
        self.progress = completed / len(self.milestones)

    def complete(self) -> None:
        self.status = "completed"
        self.progress = 1.0
        self.completed_at = time.time()
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "description": self.description,
            "category": self.category,
            "deadline": self.deadline,
            "priority": self.priority,
            "progress": self.progress,
            "milestones": self.milestones,
            "actions_taken": len(self.actions_taken),
            "outcomes": len(self.outcomes),
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> LifeGoal:
        goal = cls(
            description=data.get("description", ""),
            category=data.get("category", "general"),
            deadline=data.get("deadline"),
            priority=data.get("priority", 5),
        )
        goal.progress = data.get("progress", 0.0)
        goal.milestones = data.get("milestones", [])
        goal.actions_taken = data.get("actions_taken", []) if isinstance(data.get("actions_taken"), list) else []
        goal.outcomes = data.get("outcomes", []) if isinstance(data.get("outcomes"), list) else []
        goal.status = data.get("status", "active")
        goal.created_at = data.get("created_at", time.time())
        goal.updated_at = data.get("updated_at", time.time())
        goal.completed_at = data.get("completed_at")
        return goal


class LifeGoalManager:
    """
    Manages persistent life goals tracked over months/years.

    Example:
    Goal: Get software job
    Milestones:
    - Learn Python (done)
    - Learn web frameworks (in progress)
    - Build portfolio projects (pending)
    - Apply to jobs (pending)
    - Interview prep (pending)

    SPARK remembers this for months.
    Tracks progress continuously.
    Suggests actions.
    Updates plans.
    Measures outcomes.
    """

    def __init__(self, storage_path: str = "spark_dev_memory/life_goals.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._goals: list[LifeGoal] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._goals = [LifeGoal.from_dict(g) for g in data.get("goals", [])]
            except Exception:
                pass

    def _save(self) -> None:
        data = {"goals": [g.to_dict() for g in self._goals], "updated_at": time.time()}
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def add_goal(self, description: str, category: str = "general", deadline: float | None = None, priority: int = 5) -> LifeGoal:
        goal = LifeGoal(description, category, deadline, priority)
        self._goals.append(goal)
        self._save()
        logger.info("Life goal added: %s", description)
        return goal

    def get_goal(self, description: str) -> LifeGoal | None:
        for g in self._goals:
            if g.description == description:
                return g
        return None

    def active_goals(self) -> list[LifeGoal]:
        return [g for g in self._goals if g.status == "active"]

    def completed_goals(self) -> list[LifeGoal]:
        return [g for g in self._goals if g.status == "completed"]

    def add_milestone(self, goal_description: str, milestone: str, completed: bool = False) -> bool:
        goal = self.get_goal(goal_description)
        if goal:
            goal.add_milestone(milestone, completed)
            self._save()
            return True
        return False

    def record_action(self, goal_description: str, action: str, result: str, success: bool) -> bool:
        goal = self.get_goal(goal_description)
        if goal:
            goal.record_action(action, result, success)
            self._save()
            return True
        return False

    def get_progress_report(self) -> dict[str, Any]:
        active = self.active_goals()
        completed = self.completed_goals()
        return {
            "active_count": len(active),
            "completed_count": len(completed),
            "active_goals": [
                {
                    "description": g.description,
                    "progress": g.progress,
                    "milestones": len(g.milestones),
                    "completed_milestones": sum(1 for m in g.milestones if m.get("completed")),
                    "actions_taken": len(g.actions_taken),
                    "days_active": (time.time() - g.created_at) / 86400,
                }
                for g in active
            ],
        }

    def suggest_next_actions(self, goal_description: str) -> list[str]:
        goal = self.get_goal(goal_description)
        if not goal:
            return []

        suggestions = []
        incomplete = [m for m in goal.milestones if not m.get("completed")]
        if incomplete:
            suggestions.append(f"Continue working on: {incomplete[0]['description']}")

        failed_actions = [a for a in goal.actions_taken if not a.get("success")]
        if failed_actions:
            suggestions.append(f"Retry or rethink: {failed_actions[-1]['action']}")

        if goal.deadline:
            remaining = goal.deadline - time.time()
            if remaining < 0:
                suggestions.append("Goal deadline has passed — consider revising")
            elif remaining < 7 * 86400:
                suggestions.append(f"Deadline in {remaining / 86400:.0f} days — increase focus")

        return suggestions

    def snapshot(self) -> dict[str, Any]:
        return {
            "goals": [g.to_dict() for g in self._goals],
            "report": self.get_progress_report(),
        }
