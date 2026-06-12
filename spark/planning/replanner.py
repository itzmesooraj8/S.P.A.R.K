"""Auto Replanner — Autonomous replanning when plans fail."""

from __future__ import annotations

import logging
import time
from typing import Any

from spark.planning.llm_planner import LLMPlanner

logger = logging.getLogger("spark.planning.replanner")


class AutoReplanner:
    """
    Autonomous replanning when execution fails.

    Plan failed → Generate alternative → Continue
    """

    def __init__(self, llm_planner: LLMPlanner | None = None) -> None:
        self._planner = llm_planner or LLMPlanner()
        self._replan_history: list[dict[str, Any]] = []
        self._max_replans = 5

    async def replan(self, goal: str, failed_step: dict[str, Any], error: str, current_progress: list[dict[str, Any]], context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Generate an alternative plan after failure."""
        if len(self._replan_history) >= self._max_replans:
            logger.warning("Max replans reached for goal: %s", goal)
            return {"error": "Max replans reached", "action": "abort"}

        prompt = self._build_replan_prompt(goal, failed_step, error, current_progress, context)
        response = await self._planner._call_llm(prompt)
        new_plan = self._parse_replan(response)

        self._replan_history.append({
            "goal": goal,
            "failed_step": failed_step,
            "error": error,
            "new_plan": new_plan,
            "timestamp": time.time(),
        })

        return new_plan

    async def suggest_alternative(self, action: str, error: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Suggest an alternative action when one fails."""
        prompt = f"""The action "{action}" failed with error: {error}

Context: {context or {}}

Suggest an alternative approach. Return JSON:
{{
    "alternative": "description of alternative action",
    "tool_needed": "tool name",
    "args": {{}},
    "reasoning": "why this alternative might work"
}}

Return ONLY the JSON."""

        response = await self._planner._call_llm(prompt)
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return __import__("json").loads(response[start:end])
        except Exception:
            pass
        return {"alternative": "Try a different approach", "tool_needed": None, "args": {}}

    def _build_replan_prompt(self, goal: str, failed_step: dict, error: str, progress: list[dict], context: dict | None) -> str:
        completed = [p for p in progress if p.get("status") == "done"]
        remaining = [p for p in progress if p.get("status") != "done"]
        return f"""The current plan failed. Generate an alternative.

GOAL: {goal}

FAILED STEP: {failed_step.get("description", "unknown")}
ERROR: {error}

COMPLETED STEPS: {len(completed)}
REMAINING STEPS: {len(remaining)}

Generate a new plan that avoids the failed approach. Return JSON:
{{
    "goal": "{goal}",
    "steps": [...],
    "replan_reason": "why this new approach"
}}

Return ONLY the JSON."""

    def _parse_replan(self, response: str) -> dict[str, Any]:
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return __import__("json").loads(response[start:end])
        except Exception:
            pass
        return {"error": "Failed to parse replan", "steps": []}

    def reset(self) -> None:
        self._replan_history.clear()

    def history(self) -> list[dict[str, Any]]:
        return list(self._replan_history)
