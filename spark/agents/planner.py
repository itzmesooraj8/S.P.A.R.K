"""Planner Agent — Creates and manages plans."""

from __future__ import annotations

import logging
import time
from typing import Any

from spark.agents.base import BaseAgent, AgentStatus
from spark.cognition.goal_engine import GoalEngine, Goal
from spark.cognition.planner import TaskPlanner

logger = logging.getLogger("spark.agents.planner")


class PlannerAgent(BaseAgent):
    """Creates plans from goals and manages goal lifecycle."""

    def __init__(self, event_bus=None):
        super().__init__("planner", event_bus)
        self.goal_engine = GoalEngine()
        self.task_planner = TaskPlanner()

    async def run(self, objective: str, priority: int = 5, **kwargs) -> dict[str, Any]:
        self.status = AgentStatus.RUNNING
        self.emit("planner.start", {"objective": objective})

        try:
            goal = self.goal_engine.create_goal(objective, priority)
            plan = self.task_planner.auto_plan(goal)
            self.status = AgentStatus.IDLE
            self._last_run = time.time()

            result = {
                "goal_id": goal.id,
                "plan_id": plan.id,
                "steps": len(plan.steps),
                "status": "created",
            }
            self.emit("planner.plan_created", result)
            return result
        except Exception as exc:
            self.status = AgentStatus.ERROR
            return {"error": str(exc)}

    def next_task(self) -> dict[str, Any] | None:
        action = self.goal_engine.next_action()
        if action:
            goal, subtask = action
            return {
                "goal_id": goal.id,
                "subtask_id": subtask.id,
                "description": subtask.description,
                "tool_needed": subtask.tool_needed,
                "args": subtask.args,
            }
        return None

    def complete_task(self, goal_id: str, subtask_id: str, result: str, success: bool = True) -> None:
        self.goal_engine.complete_subtask(goal_id, subtask_id, result, success)

    def stats(self) -> dict[str, Any]:
        return self.goal_engine.stats()
