"""Preference Learner — Infers user preferences from behavior patterns."""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.user.preferences")


class PreferenceLearner:
    """
    Infers user preferences from behavior patterns.

    Without this, SPARK asks "what do you prefer?"
    With this, SPARK knows before you tell it.

    Learns:
    - Workflow sequences (VS Code → Terminal → GitHub)
    - Tool preferences (always uses Playwright, never Selenium)
    - Time patterns (codes at night, emails in morning)
    - Communication style (prefers concise responses)
    - Project priorities (works on Project A before Project B)
    """

    def __init__(self, storage_path: str = "spark_dev_memory/preferences.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._sequences: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._tool_scores: dict[str, dict[str, float]] = defaultdict(lambda: {"uses": 0, "successes": 0})
        self._time_patterns: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self._workflow_graph: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._inferred: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._sequences = defaultdict(list, data.get("sequences", {}))
                self._tool_scores = defaultdict(lambda: {"uses": 0, "successes": 0}, data.get("tool_scores", {}))
                self._time_patterns = defaultdict(lambda: defaultdict(int), data.get("time_patterns", {}))
                self._workflow_graph = defaultdict(lambda: defaultdict(int), data.get("workflow_graph", {}))
                self._inferred = data.get("inferred", {})
            except Exception:
                pass

    def _save(self) -> None:
        data = {
            "sequences": dict(self._sequences),
            "tool_scores": dict(self._tool_scores),
            "time_patterns": {k: dict(v) for k, v in self._time_patterns.items()},
            "workflow_graph": {k: dict(v) for k, v in self._workflow_graph.items()},
            "inferred": self._inferred,
            "updated_at": time.time(),
        }
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def observe_action(self, action: str, context: dict[str, Any] | None = None) -> None:
        ctx = context or {}
        hour = ctx.get("hour", time.localtime().tm_hour)
        app = ctx.get("app", "unknown")

        self._time_patterns[action][hour] += 1
        self._workflow_graph[app][action] += 1

        sequence_key = ctx.get("session_id", "default")
        self._sequences[sequence_key].append({
            "action": action,
            "app": app,
            "hour": hour,
            "timestamp": time.time(),
        })
        if len(self._sequences[sequence_key]) > 50:
            self._sequences[sequence_key] = self._sequences[sequence_key][-50:]

        self._infer_preferences()
        self._save()

    def observe_tool_use(self, tool: str, success: bool) -> None:
        self._tool_scores[tool]["uses"] += 1
        if success:
            self._tool_scores[tool]["successes"] += 1
        self._infer_preferences()
        self._save()

    def _infer_preferences(self) -> None:
        self._inferred["preferred_tools"] = {}
        for tool, scores in self._tool_scores.items():
            if scores["uses"] >= 3:
                rate = scores["successes"] / scores["uses"]
                self._inferred["preferred_tools"][tool] = {
                    "success_rate": rate,
                    "recommendation": "prefer" if rate > 0.8 else "avoid" if rate < 0.4 else "neutral",
                }

        self._inferred["active_hours"] = {}
        for action, hours in self._time_patterns.items():
            if hours:
                peak_hour = max(hours, key=hours.get)
                self._inferred["active_hours"][action] = peak_hour

        self._inferred["common_workflows"] = []
        for app, actions in self._workflow_graph.items():
            if actions:
                top_action = max(actions, key=actions.get)
                self._inferred["common_workflows"].append({
                    "after_app": app,
                    "likely_action": top_action,
                    "confidence": actions[top_action] / sum(actions.values()),
                })

    def get_preferred_tool(self, category: str) -> str | None:
        preferred = self._inferred.get("preferred_tools", {})
        best = None
        best_rate = 0.0
        for tool, info in preferred.items():
            if category.lower() in tool.lower():
                if info.get("success_rate", 0) > best_rate:
                    best_rate = info["success_rate"]
                    best = tool
        return best

    def predict_next_action(self, current_app: str) -> str | None:
        workflows = self._inferred.get("common_workflows", [])
        for w in workflows:
            if w.get("after_app", "").lower() == current_app.lower():
                if w.get("confidence", 0) > 0.6:
                    return w.get("likely_action")
        return None

    def get_peak_hours(self, action: str) -> list[int]:
        hours = self._time_patterns.get(action, {})
        if not hours:
            return []
        sorted_hours = sorted(hours.items(), key=lambda x: x[1], reverse=True)
        return [h for h, _ in sorted_hours[:3]]

    def get_workflow_suggestions(self, current_app: str) -> list[dict[str, Any]]:
        suggestions = []
        for w in self._inferred.get("common_workflows", []):
            if w.get("after_app", "").lower() == current_app.lower():
                suggestions.append(w)
        return suggestions

    def snapshot(self) -> dict[str, Any]:
        return {
            "inferred": self._inferred,
            "tool_scores": dict(self._tool_scores),
            "workflow_count": len(self._workflow_graph),
        }
