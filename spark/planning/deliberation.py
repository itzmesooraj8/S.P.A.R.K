"""Multi-Agent Deliberation — Agents discuss before acting.

Planner Agent: How should I solve this?
Executor Agent: Can I actually do it?
Reflection Agent: What went wrong?
Consensus: New plan
"""

from __future__ import annotations

import logging
import time
from typing import Any

from spark.planning.llm_planner import LLMPlanner

logger = logging.getLogger("spark.planning.deliberation")


class AgentVote:
    def __init__(self, agent_name: str, proposal: str, confidence: float, concerns: list[str] | None = None):
        self.agent_name = agent_name
        self.proposal = proposal
        self.confidence = confidence
        self.concerns = concerns or []
        self.timestamp = time.time()


class DeliberationResult:
    def __init__(self, consensus: str, final_plan: dict[str, Any], votes: list[AgentVote], confidence: float):
        self.consensus = consensus
        self.final_plan = final_plan
        self.votes = votes
        self.confidence = confidence
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "consensus": self.consensus,
            "final_plan": self.final_plan,
            "votes": [
                {"agent": v.agent_name, "proposal": v.proposal, "confidence": v.confidence, "concerns": v.concerns}
                for v in self.votes
            ],
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


class MultiAgentDeliberation:
    """
    Multiple agents deliberate before acting.

    Each agent provides their perspective:
    - Planner: What should we do?
    - Executor: Can we do it?
    - Observer: What's the current state?
    - Reflection: What has worked before?

    Consensus is reached and a final plan is created.
    """

    def __init__(self, llm_planner: LLMPlanner | None = None) -> None:
        self._planner = llm_planner or LLMPlanner()
        self._history: list[DeliberationResult] = []

    async def deliberate(self, goal: str, context: dict[str, Any] | None = None, available_tools: list[str] | None = None) -> DeliberationResult:
        """Run multi-agent deliberation for a goal."""
        votes = []

        planner_vote = await self._planner_perspective(goal, context, available_tools)
        votes.append(planner_vote)

        executor_vote = await self._executor_perspective(goal, context, available_tools)
        votes.append(executor_vote)

        reflection_vote = await self._reflection_perspective(goal, context)
        votes.append(reflection_vote)

        consensus = self._reach_consensus(votes)
        final_plan = await self._synthesize_plan(goal, votes, context)

        result = DeliberationResult(
            consensus=consensus["decision"],
            final_plan=final_plan,
            votes=votes,
            confidence=consensus["confidence"],
        )
        self._history.append(result)
        return result

    async def _planner_perspective(self, goal: str, context: dict | None, tools: list[str] | None) -> AgentVote:
        prompt = f"""As the PLANNER agent, propose how to achieve this goal:

GOAL: {goal}
CONTEXT: {context or {}}
TOOLS: {tools or []}

Return JSON:
{{
    "proposal": "detailed plan description",
    "confidence": 0.0-1.0,
    "concerns": ["list of concerns"]
}}"""
        response = await self._planner._call_llm(prompt)
        parsed = self._parse_vote(response)
        return AgentVote("planner", parsed.get("proposal", ""), parsed.get("confidence", 0.5), parsed.get("concerns", []))

    async def _executor_perspective(self, goal: str, context: dict | None, tools: list[str] | None) -> AgentVote:
        prompt = f"""As the EXECUTOR agent, assess if this goal can be executed:

GOAL: {goal}
AVAILABLE TOOLS: {tools or []}

Return JSON:
{{
    "proposal": "execution feasibility assessment",
    "confidence": 0.0-1.0,
    "concerns": ["list of execution concerns"]
}}"""
        response = await self._planner._call_llm(prompt)
        parsed = self._parse_vote(response)
        return AgentVote("executor", parsed.get("proposal", ""), parsed.get("confidence", 0.5), parsed.get("concerns", []))

    async def _reflection_perspective(self, goal: str, context: dict | None) -> AgentVote:
        prompt = f"""As the REFLECTION agent, consider past experience for this goal:

GOAL: {goal}
CONTEXT: {context or {}}

Return JSON:
{{
    "proposal": "recommendation based on past experience",
    "confidence": 0.0-1.0,
    "concerns": ["lessons learned"]
}}"""
        response = await self._planner._call_llm(prompt)
        parsed = self._parse_vote(response)
        return AgentVote("reflection", parsed.get("proposal", ""), parsed.get("confidence", 0.5), parsed.get("concerns", []))

    def _reach_consensus(self, votes: list[AgentVote]) -> dict[str, Any]:
        avg_confidence = sum(v.confidence for v in votes) / len(votes) if votes else 0.0
        all_concerns = []
        for v in votes:
            all_concerns.extend(v.concerns)

        if avg_confidence > 0.7 and len(all_concerns) < 3:
            decision = "proceed"
        elif avg_confidence > 0.4:
            decision = "proceed_with_caution"
        else:
            decision = "reconsider"

        return {"decision": decision, "confidence": avg_confidence, "concerns": all_concerns}

    async def _synthesize_plan(self, goal: str, votes: list[AgentVote], context: dict | None) -> dict[str, Any]:
        proposals = "\n".join([f"- {v.agent_name}: {v.proposal}" for v in votes])
        prompt = f"""Synthesize these agent proposals into a final plan:

GOAL: {goal}
PROPOSALS:
{proposals}

Return JSON plan with steps."""
        response = await self._planner._call_llm(prompt)
        return self._planner._parse_plan(response)

    def _parse_vote(self, response: str) -> dict[str, Any]:
        try:
            start = response.find("{")
            end = response.rfind("}") + 1
            if start >= 0 and end > start:
                return __import__("json").loads(response[start:end])
        except Exception:
            pass
        return {"proposal": response[:200], "confidence": 0.5, "concerns": []}

    def history(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._history]
