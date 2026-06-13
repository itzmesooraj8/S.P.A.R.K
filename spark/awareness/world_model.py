"""World Model — Understands what user is doing, trying to do, usually does, will need next.

JARVIS-style systems know:
- What user is doing
- What user is trying to do
- What user usually does
- What user will likely need next
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.awareness.world_model")


class ActivityPattern:
    def __init__(self, name: str, apps: list[str], description: str = ""):
        self.name = name
        self.apps = apps
        self.description = description
        self.confidence = 0.0
        self.last_seen = 0.0
        self.occurrences = 0


class WorldModel:
    """
    Maintains a model of the user's world.

    Infers activity patterns from observations.
    Predicts what the user will likely need next.
    """

    def __init__(self) -> None:
        self._patterns: dict[str, ActivityPattern] = {}
        self._current_activity: str = "unknown"
        self._activity_history: list[dict[str, Any]] = []
        self._predictions: list[dict[str, Any]] = []
        self._user_habits: dict[str, Any] = {
            "frequent_apps": {},
            "time_patterns": {},
            "common_workflows": [],
        }
        self._register_default_patterns()

    def _register_default_patterns(self) -> None:
        self.register_pattern(ActivityPattern(
            name="software_development",
            apps=["code.exe", "Code", "Terminal", "git", "python", "cursor.exe"],
            description="Software development session",
        ))
        self.register_pattern(ActivityPattern(
            name="research",
            apps=["chrome.exe", "firefox.exe", "msedge.exe"],
            description="Web research / browsing",
        ))
        self.register_pattern(ActivityPattern(
            name="communication",
            apps=["discord.exe", "slack.exe", "teams.exe", "whatsapp.exe"],
            description="Communication / messaging",
        ))
        self.register_pattern(ActivityPattern(
            name="creative_work",
            apps=["figma.exe", "photoshop.exe", "blender.exe"],
            description="Creative / design work",
        ))
        self.register_pattern(ActivityPattern(
            name="document_work",
            apps=["notepad.exe", "word.exe", "obsidian.exe", "typora.exe"],
            description="Document editing / writing",
        ))

    def register_pattern(self, pattern: ActivityPattern) -> None:
        self._patterns[pattern.name] = pattern

    def observe(self, observation: dict[str, Any]) -> dict[str, Any]:
        """Update world model from new observation."""
        apps = observation.get("application", {})
        focused = apps.get("focused", "")
        active = apps.get("active", [])

        detected = self._detect_activity(focused, active)
        self._current_activity = detected

        entry = {
            "activity": detected,
            "focused_app": focused,
            "timestamp": time.time(),
        }
        self._activity_history.append(entry)
        if len(self._activity_history) > 200:
            self._activity_history = self._activity_history[-200:]

        self._update_habits(focused, active)
        predictions = self._predict_needs(detected, focused)

        result = {
            "current_activity": detected,
            "confidence": self._patterns.get(detected, ActivityPattern("", [])).confidence,
            "predictions": predictions,
        }
        return result

    def _detect_activity(self, focused: str, active: list[str]) -> str:
        focused_lower = focused.lower()
        best_match = "unknown"
        best_score = 0.0

        for name, pattern in self._patterns.items():
            score = 0.0
            for app in pattern.apps:
                if app.lower() in focused_lower:
                    score += 1.0
                for active_app in active:
                    if app.lower() in active_app.lower():
                        score += 0.3
            if score > best_score:
                best_score = score
                best_match = name
                pattern.confidence = min(score / 2.0, 1.0)
                pattern.last_seen = time.time()
                pattern.occurrences += 1

        return best_match

    def _predict_needs(self, activity: str, focused: str) -> list[dict[str, Any]]:
        if len(self._activity_history) < 3:
            return []

        recent = self._activity_history[-10:]
        total = len(recent)

        activity_counts: dict[str, int] = {}
        for entry in recent:
            act = entry.get("activity", "unknown")
            activity_counts[act] = activity_counts.get(act, 0) + 1

        app_counts: dict[str, int] = {}
        for entry in recent:
            app = entry.get("focused_app", "")
            if app:
                app_counts[app] = app_counts.get(app, 0) + 1

        predictions = []

        if activity == "software_development":
            dev_confidence = activity_counts.get("software_development", 0) / total
            if dev_confidence >= 0.3:
                predictions.append({"need": "terminal_access", "confidence": dev_confidence, "reason": f"dev activity {dev_confidence:.0%} of recent"})
                predictions.append({"need": "web_search", "confidence": dev_confidence * 0.75, "reason": "likely researching code"})

        elif activity == "research":
            research_confidence = activity_counts.get("research", 0) / total
            if research_confidence >= 0.3:
                predictions.append({"need": "bookmark_management", "confidence": research_confidence, "reason": f"research {research_confidence:.0%} of recent"})
                predictions.append({"need": "note_taking", "confidence": research_confidence * 0.7, "reason": "research findings"})

        elif activity == "communication":
            comm_confidence = activity_counts.get("communication", 0) / total
            if comm_confidence >= 0.3:
                predictions.append({"need": "message_summarization", "confidence": comm_confidence, "reason": f"communication {comm_confidence:.0%} of recent"})

        return predictions

    def _update_habits(self, focused: str, active: list[str]) -> None:
        if focused:
            apps = self._user_habits["frequent_apps"]
            apps[focused] = apps.get(focused, 0) + 1

    def get_current_activity(self) -> str:
        return self._current_activity

    def get_predictions(self) -> list[dict[str, Any]]:
        return self._predict_needs(self._current_activity, "")

    def get_habits(self) -> dict[str, Any]:
        return dict(self._user_habits)

    def snapshot(self) -> dict[str, Any]:
        return {
            "current_activity": self._current_activity,
            "predictions": self.get_predictions(),
            "habits": self.get_habits(),
            "activity_count": len(self._activity_history),
            "patterns": {k: {"confidence": v.confidence, "occurrences": v.occurrences} for k, v in self._patterns.items()},
        }
