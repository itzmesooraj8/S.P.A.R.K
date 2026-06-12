"""Reflection Engine — Self-evaluation that actually influences future behavior.

Real reflection:
Action Failed → Reflection → New Strategy → Future Planning Updated

Reflection must modify behavior. Otherwise it is just logging.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.cognition.reflection")


class Insight:
    def __init__(self, pattern: str, recommendation: str, impact: str = "low"):
        self.pattern = pattern
        self.recommendation = recommendation
        self.impact = impact
        self.applied = False
        self.applied_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "pattern": self.pattern,
            "recommendation": self.recommendation,
            "impact": self.impact,
            "applied": self.applied,
        }


class ReflectionEntry:
    def __init__(self, actions: list[dict[str, Any]], context: dict[str, Any] | None = None):
        self.timestamp = time.time()
        self.actions_analyzed = len(actions)
        self.insights: list[Insight] = []
        self.patterns: list[str] = []
        self.strategy_changes: list[str] = []
        self.context = context or {}
        self.applied = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "actions_analyzed": self.actions_analyzed,
            "insights": [i.to_dict() for i in self.insights],
            "patterns": self.patterns,
            "strategy_changes": self.strategy_changes,
            "applied": self.applied,
        }


class ReflectionEngine:
    """
    Self-reflection that modifies behavior.

    When an action fails:
    1. Detect the failure pattern
    2. Generate insight
    3. Create strategy change
    4. Apply to future planning
    """

    def __init__(self, storage_path: str = "spark_dev_memory/reflections.jsonl") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._reflections: list[ReflectionEntry] = []
        self._last_reflection: float = 0.0
        self.reflection_interval: float = 3600.0
        self._strategy_modifiers: dict[str, Any] = {
            "avoid_tools": [],
            "prefer_tools": [],
            "retry_patterns": {},
            "risk_adjustments": {},
        }

    def should_reflect(self) -> bool:
        return time.time() - self._last_reflection >= self.reflection_interval

    def reflect(self, recent_actions: list[dict[str, Any]], context: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = ReflectionEntry(recent_actions, context)

        entry.patterns = self._detect_patterns(recent_actions)
        entry.insights = self._generate_insights(recent_actions, entry.patterns)
        entry.strategy_changes = self._generate_strategy_changes(entry.insights)

        self._apply_strategy_changes(entry.strategy_changes)

        self._reflections.append(entry)
        self._last_reflection = time.time()

        self._persist(entry)

        logger.info(
            "Reflection: %d insights, %d strategy changes from %d actions",
            len(entry.insights), len(entry.strategy_changes), len(recent_actions),
        )
        return entry.to_dict()

    def reflect_on_failure(self, action: dict[str, Any], error: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        entry = ReflectionEntry([action], context)
        entry.patterns = [f"failure_in_{action.get('tool', 'unknown')}"]
        entry.insights = [
            Insight(
                pattern=f"Tool '{action.get('tool', 'unknown')}' failed: {error}",
                recommendation=f"Consider alternative approach for {action.get('tool', 'unknown')}",
                impact="high",
            )
        ]
        entry.strategy_changes = [f"avoid_{action.get('tool', 'unknown')}_on_failure"]
        self._apply_strategy_changes(entry.strategy_changes)
        self._reflections.append(entry)
        self._persist(entry)
        return entry.to_dict()

    def _detect_patterns(self, actions: list[dict[str, Any]]) -> list[str]:
        patterns = []
        if len(actions) < 3:
            return patterns

        tools_used = [a.get("tool", "unknown") for a in actions]
        unique_tools = set(tools_used)
        if len(unique_tools) == 1:
            patterns.append(f"Repetitive tool usage: {unique_tools.pop()}")

        failed = [a for a in actions if a.get("success") is False]
        if len(failed) > len(actions) * 0.3:
            patterns.append(f"High failure rate: {len(failed)}/{len(actions)}")

        long_actions = [a for a in actions if a.get("duration", 0) > 30]
        if long_actions:
            patterns.append(f"Slow actions detected: {len(long_actions)}")

        return patterns

    def _generate_insights(self, actions: list[dict[str, Any]], patterns: list[str]) -> list[Insight]:
        insights = []
        for pattern in patterns:
            if "Repetitive" in pattern:
                insights.append(Insight(
                    pattern=pattern,
                    recommendation="Diversify tool usage to avoid loops",
                    impact="medium",
                ))
            elif "failure" in pattern.lower():
                insights.append(Insight(
                    pattern=pattern,
                    recommendation="Review error patterns and adjust strategy",
                    impact="high",
                ))
            elif "Slow" in pattern:
                insights.append(Insight(
                    pattern=pattern,
                    recommendation="Consider async operations or parallelization",
                    impact="medium",
                ))
        return insights

    def _generate_strategy_changes(self, insights: list[Insight]) -> list[str]:
        changes = []
        for insight in insights:
            if insight.impact == "high":
                changes.append(f"priority_adjustment_{insight.pattern.split(':')[0].lower().replace(' ', '_')}")
            elif insight.impact == "medium":
                changes.append(f"approach_adjustment_{insight.pattern.split(':')[0].lower().replace(' ', '_')}")
        return changes

    def _apply_strategy_changes(self, changes: list[str]) -> None:
        for change in changes:
            if change.startswith("priority_adjustment"):
                self._strategy_modifiers["risk_adjustments"][change] = "increase_care"
            elif change.startswith("approach_adjustment"):
                self._strategy_modifiers["retry_patterns"][change] = "try_different_approach"
            logger.debug("Strategy change applied: %s", change)

    def get_strategy_modifiers(self) -> dict[str, Any]:
        return dict(self._strategy_modifiers)

    def should_avoid_tool(self, tool_name: str) -> bool:
        return tool_name in self._strategy_modifiers.get("avoid_tools", [])

    def get_preferred_tools(self) -> list[str]:
        return list(self._strategy_modifiers.get("prefer_tools", []))

    def recent(self, limit: int = 10) -> list[dict[str, Any]]:
        return [r.to_dict() for r in self._reflections[-limit:]]

    def _persist(self, entry: ReflectionEntry) -> None:
        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("Reflection persist failed: %s", exc)

    def stats(self) -> dict[str, Any]:
        return {
            "total_reflections": len(self._reflections),
            "total_insights": sum(len(r.insights) for r in self._reflections),
            "strategy_modifiers": self._strategy_modifiers,
        }
