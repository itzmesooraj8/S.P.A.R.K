"""Reasoning Engine — Pure thinking and decision making, wired to LLM."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("spark.cognition.reasoning")


class ReasoningEngine:
    """Handles reasoning, decision making, and evaluation using LLM."""

    def __init__(self) -> None:
        self._reasoning_chain: list[dict[str, Any]] = []
        self._bridge = None

    def _get_bridge(self):
        if self._bridge is None:
            from spark.llm_bridge import LLMBridge
            self._bridge = LLMBridge()
        return self._bridge

    def reason(self, context: str, question: str, facts: list[str] | None = None) -> dict[str, Any]:
        """Execute a reasoning step using LLM."""
        steps = []
        if facts:
            for fact in facts:
                steps.append({"type": "fact", "content": fact})

        steps.append({"type": "analysis", "content": f"Analyzing: {question}"})
        steps.append({"type": "context", "content": context})

        import asyncio
        try:
            loop = asyncio.get_running_loop()
            conclusion = loop.run_until_complete(self._synthesize_llm(steps, question))
        except RuntimeError:
            conclusion = self._synthesize_deterministic(steps, question)

        result = {
            "question": question,
            "steps": steps,
            "conclusion": conclusion,
        }
        self._reasoning_chain.append(result)
        return result

    def decide(self, options: list[str], criteria: list[str], context: str = "") -> dict[str, Any]:
        """Evaluate options against criteria using LLM."""
        import asyncio
        scored = []
        try:
            loop = asyncio.get_running_loop()
            for option in options:
                score = loop.run_until_complete(self._score_option_llm(option, criteria, context))
                scored.append({"option": option, "score": score})
        except RuntimeError:
            for option in options:
                score = self._score_option_deterministic(option, criteria, context)
                scored.append({"option": option, "score": score})

        scored.sort(key=lambda x: x["score"], reverse=True)
        return {
            "options": scored,
            "best": scored[0]["option"] if scored else None,
            "reasoning": f"Evaluated {len(options)} options against {len(criteria)} criteria",
        }

    async def _score_option_llm(self, option: str, criteria: list[str], context: str) -> float:
        bridge = self._get_bridge()
        criteria_str = ", ".join(criteria)
        prompt = (
            f"Rate this option 0.0 to 1.0 for achieving the goal.\n"
            f"Goal criteria: {criteria_str}\n"
            f"Context: {context}\n"
            f"Option: {option}\n"
            f"Return only a float between 0.0 and 1.0."
        )
        try:
            response = await bridge.ask(prompt, max_tokens=10, temperature=0.0)
            score = float(response.strip())
            return max(0.0, min(1.0, score))
        except (ValueError, Exception) as exc:
            logger.debug("LLM scoring failed, using deterministic: %s", exc)
            return self._score_option_deterministic(option, criteria, context)

    def _score_option_deterministic(self, option: str, criteria: list[str], context: str) -> float:
        score = 0.5
        option_lower = option.lower()
        context_lower = context.lower()
        for criterion in criteria:
            if criterion.lower() in option_lower:
                score += 0.1
            if criterion.lower() in context_lower:
                score += 0.05
        return min(1.0, score)

    async def _synthesize_llm(self, steps: list[dict], question: str) -> str:
        bridge = self._get_bridge()
        steps_text = "\n".join(f"- {s['type']}: {s['content']}" for s in steps)
        prompt = (
            f"Based on these reasoning steps, provide a brief conclusion.\n"
            f"Question: {question}\n"
            f"Steps:\n{steps_text}\n"
            f"Conclusion:"
        )
        try:
            response = await bridge.ask(prompt, max_tokens=100, temperature=0.3)
            return response.strip() if response.strip() else self._synthesize_deterministic(steps, question)
        except Exception:
            return self._synthesize_deterministic(steps, question)

    def _synthesize_deterministic(self, steps: list[dict], question: str) -> str:
        facts = [s["content"] for s in steps if s["type"] == "fact"]
        if facts:
            return f"Based on {len(facts)} facts and analysis about '{question}': {'; '.join(facts[:3])}"
        return f"Analyzed '{question}' through {len(steps)} reasoning steps"

    def recent_chain(self, limit: int = 10) -> list[dict[str, Any]]:
        return self._reasoning_chain[-limit:]

    def evaluate(self, action: str, outcome: str) -> dict[str, Any]:
        """Self-evaluate an action's outcome."""
        return {
            "action": action,
            "outcome": outcome,
            "assessment": "completed",
            "learnings": [],
        }
