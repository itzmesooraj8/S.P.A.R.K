"""LLM Planner — Uses LLM to create dynamic plans from goals."""

from __future__ import annotations

import json
import logging
import time
from typing import Any

import httpx

logger = logging.getLogger("spark.planning.llm_planner")


class LLMPlanner:
    """
    Uses LLM to create detailed plans from high-level goals.

    Not rule-based. Dynamic. Adapts to context.
    """

    def __init__(self, llm_host: str = "http://localhost:11434", llm_model: str = "llama3") -> None:
        self._host = llm_host
        self._model = llm_model

    async def create_plan(self, goal: str, context: dict[str, Any] | None = None, available_tools: list[str] | None = None) -> dict[str, Any]:
        """Use LLM to create a detailed plan for a goal."""
        prompt = self._build_plan_prompt(goal, context, available_tools)
        response = await self._call_llm(prompt)
        plan = self._parse_plan(response)
        return plan

    async def create_subtasks(self, step_description: str, context: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Break a step into subtasks using LLM."""
        prompt = self._build_subtask_prompt(step_description, context)
        response = await self._call_llm(prompt)
        return self._parse_subtasks(response)

    async def evaluate_plan(self, plan: dict[str, Any], goal: str) -> dict[str, Any]:
        """Have LLM evaluate a plan's feasibility."""
        prompt = self._build_evaluate_prompt(plan, goal)
        response = await self._call_llm(prompt)
        return self._parse_evaluation(response)

    def _build_plan_prompt(self, goal: str, context: dict | None, tools: list[str] | None) -> str:
        ctx = json.dumps(context or {}, indent=2)
        tool_list = ", ".join(tools or ["web_search", "take_screenshot", "open_application", "type_text", "file_search"])
        return f"""You are SPARK, an AI operating system. Create a detailed plan for this goal.

GOAL: {goal}

CONTEXT:
{ctx}

AVAILABLE TOOLS: {tool_list}

Create a JSON plan with this structure:
{{
    "goal": "{goal}",
    "steps": [
        {{
            "id": 1,
            "description": "What to do",
            "tool_needed": "tool_name or null",
            "args": {{}},
            "reasoning": "Why this step",
            "expected_outcome": "What should happen"
        }}
    ],
    "estimated_duration": "time estimate",
    "risk_assessment": "low/medium/high",
    "dependencies": ["list of step dependencies"]
}}

Be specific. Each step should be actionable. Return ONLY the JSON."""

    def _build_subtask_prompt(self, step: str, context: dict | None) -> str:
        ctx = json.dumps(context or {}, indent=2)
        return f"""Break this task into smaller subtasks:

TASK: {step}

CONTEXT:
{ctx}

Return JSON array of subtasks:
[
    {{"description": "subtask description", "tool_needed": "tool or null", "args": {{}}}}
]

Return ONLY the JSON array."""

    def _build_evaluate_prompt(self, plan: dict, goal: str) -> str:
        return f"""Evaluate this plan for the goal:

GOAL: {goal}

PLAN:
{json.dumps(plan, indent=2)}

Return JSON:
{{
    "feasible": true/false,
    "strengths": ["list"],
    "weaknesses": ["list"],
    "suggestions": ["list"],
    "confidence": 0.0-1.0
}}

Return ONLY the JSON."""

    async def _call_llm(self, prompt: str) -> str:
        try:
            response = httpx.post(
                f"{self._host}/api/chat",
                json={
                    "model": self._model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "")
        except Exception as exc:
            logger.error("LLM call failed: %s", exc)
            return ""

    def _parse_plan(self, response: str) -> dict[str, Any]:
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
        return {
            "goal": "",
            "steps": [{"id": 1, "description": response[:200], "tool_needed": None, "args": {}}],
            "error": "Failed to parse LLM response",
        }

    def _parse_subtasks(self, response: str) -> list[dict[str, Any]]:
        try:
            start = response.find("[")
            end = response.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
        return [{"description": response[:200], "tool_needed": None, "args": {}}]

    def _parse_evaluation(self, response: str) -> dict[str, Any]:
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(response[start:end])
        except json.JSONDecodeError:
            pass
        return {"feasible": True, "confidence": 0.5, "error": "Failed to parse evaluation"}
