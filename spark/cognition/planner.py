"""Task Planner — Decomposes goals into executable subtasks."""

from __future__ import annotations

import logging
from typing import Any

from spark.cognition.goal_engine import Goal, Plan, Subtask, SubtaskStatus, GoalStatus

logger = logging.getLogger("spark.cognition.planner")


class TaskPlanner:
    """Decomposes goals into ordered subtask plans."""

    def __init__(self) -> None:
        self._plans: dict[str, Plan] = {}

    def create_plan(self, goal: Goal, steps: list[dict[str, Any]]) -> Plan:
        """Create a plan from a list of step definitions."""
        subtasks = []
        for step in steps:
            subtask = Subtask(
                description=step.get("description", ""),
                tool_needed=step.get("tool"),
                args=step.get("args", {}),
                depends_on=step.get("depends_on", []),
            )
            subtasks.append(subtask)

        plan = Plan(goal_id=goal.id, steps=subtasks)
        goal.plan = plan
        goal.status = GoalStatus.PLANNING
        self._plans[plan.id] = plan
        logger.info("Plan created for goal %s with %d steps", goal.id, len(subtasks))
        return plan

    def auto_plan(self, goal: Goal, available_tools: list[str] | None = None) -> Plan:
        """Generate a plan automatically based on goal description."""
        steps = self._decompose_goal(goal.description, available_tools or [])
        return self.create_plan(goal, steps)

    def _decompose_goal(self, description: str, available_tools: list[str]) -> list[dict[str, Any]]:
        steps = [
            {"description": f"Analyze objective: {description}", "tool": None},
            {"description": "Gather required information", "tool": "web_search"},
            {"description": "Execute primary action", "tool": None},
            {"description": "Verify outcome", "tool": "screen"},
        ]
        return steps

    def advance_plan(self, plan: Plan) -> bool:
        """Move to next subtask. Returns True if there is a next step."""
        if plan.current_step < len(plan.steps):
            current = plan.steps[plan.current_step]
            if current.status == SubtaskStatus.DONE or current.status == SubtaskStatus.FAILED:
                plan.current_step += 1
                return plan.current_step < len(plan.steps)
        return False

    def get_next_subtask(self, plan: Plan) -> Subtask | None:
        if plan.current_step < len(plan.steps):
            return plan.steps[plan.current_step]
        return None
