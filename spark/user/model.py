"""User Model — Learns and remembers everything about the user."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.user.model")


class UserModel:
    """
    Learns everything about the user over time.

    Without this, SPARK remains generic.
    With this, SPARK becomes personalized.

    Tracks:
    - Preferred tools (Playwright vs Selenium)
    - Coding style (tabs vs spaces, naming conventions)
    - Work schedule (morning person vs night owl)
    - Projects (active, archived, goals)
    - Goals (short-term, long-term, life goals)
    - Habits (frequent apps, common workflows)
    - Communication preferences (formal vs casual, verbose vs concise)
    """

    def __init__(self, storage_path: str = "spark_dev_memory/user_model.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._data: dict[str, Any] = self._load()

    def _load(self) -> dict[str, Any]:
        if self._path.exists():
            try:
                return json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return self._default_model()

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _default_model(self) -> dict[str, Any]:
        return {
            "name": "",
            "preferences": {
                "tools": {},
                "coding_style": {},
                "communication": {"formality": "professional", "verbosity": "concise"},
            },
            "schedule": {
                "active_hours": [],
                "timezone": "",
                "last_active": 0.0,
            },
            "projects": [],
            "goals": {
                "short_term": [],
                "long_term": [],
                "life_goals": [],
            },
            "habits": {
                "frequent_apps": {},
                "common_workflows": [],
                "session_patterns": [],
            },
            "skills": {
                "known": [],
                "proficient": [],
                "learning": [],
            },
            "communication_history": {
                "total_interactions": 0,
                "avg_session_length": 0,
                "preferred_topics": [],
            },
            "learned_factories": [],
            "updated_at": 0.0,
        }

    def get(self, path: str, default: Any = None) -> Any:
        parts = path.split(".")
        current = self._data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return default
            if current is None:
                return default
        return current

    def set(self, path: str, value: Any) -> None:
        parts = path.split(".")
        current = self._data
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value
        self._data["updated_at"] = time.time()
        self._save()

    def learn_tool_preference(self, tool: str, success: bool) -> None:
        tools = self._data.setdefault("preferences", {}).setdefault("tools", {})
        if tool not in tools:
            tools[tool] = {"uses": 0, "successes": 0, "success_rate": 0.0}
        tools[tool]["uses"] += 1
        if success:
            tools[tool]["successes"] += 1
        tools[tool]["success_rate"] = tools[tool]["successes"] / tools[tool]["uses"]
        self._save()

    def get_preferred_tool(self, category: str) -> str | None:
        tools = self._data.get("preferences", {}).get("tools", {})
        best_tool = None
        best_rate = 0.0
        for tool_name, stats in tools.items():
            if category.lower() in tool_name.lower():
                if stats.get("success_rate", 0) > best_rate:
                    best_rate = stats["success_rate"]
                    best_tool = tool_name
        return best_tool

    def add_project(self, name: str, description: str = "", status: str = "active") -> None:
        projects = self._data.setdefault("projects", [])
        existing = [p for p in projects if p.get("name") == name]
        if existing:
            existing[0]["status"] = status
            existing[0]["updated_at"] = time.time()
        else:
            projects.append({
                "name": name,
                "description": description,
                "status": status,
                "created_at": time.time(),
                "updated_at": time.time(),
            })
        self._save()

    def add_goal(self, goal: str, category: str = "short_term", deadline: float | None = None) -> None:
        goals = self._data.setdefault("goals", {}).setdefault(category, [])
        goals.append({
            "description": goal,
            "deadline": deadline,
            "created_at": time.time(),
            "progress": 0.0,
            "status": "active",
        })
        self._save()

    def add_habit(self, habit: str, context: str = "") -> None:
        habits = self._data.setdefault("habits", {}).setdefault("common_workflows", [])
        existing = [h for h in habits if h.get("description") == habit]
        if existing:
            existing[0]["count"] = existing[0].get("count", 0) + 1
            existing[0]["last_seen"] = time.time()
        else:
            habits.append({
                "description": habit,
                "context": context,
                "count": 1,
                "first_seen": time.time(),
                "last_seen": time.time(),
            })
        self._save()

    def track_active_hours(self, hour: int) -> None:
        schedule = self._data.setdefault("schedule", {})
        active = schedule.setdefault("active_hours", [])
        hour_entry = [h for h in active if h.get("hour") == hour]
        if hour_entry:
            hour_entry[0]["count"] = hour_entry[0].get("count", 0) + 1
        else:
            active.append({"hour": hour, "count": 1})
        schedule["last_active"] = time.time()
        self._save()

    def increment_interactions(self) -> None:
        history = self._data.setdefault("communication_history", {})
        history["total_interactions"] = history.get("total_interactions", 0) + 1
        self._save()

    def get_profile(self) -> dict[str, Any]:
        return {
            "name": self._data.get("name", ""),
            "preferred_tools": self._data.get("preferences", {}).get("tools", {}),
            "active_projects": [p for p in self._data.get("projects", []) if p.get("status") == "active"],
            "goals": self._data.get("goals", {}),
            "habits": self._data.get("habits", {}).get("common_workflows", []),
            "total_interactions": self._data.get("communication_history", {}).get("total_interactions", 0),
        }

    def snapshot(self) -> dict[str, Any]:
        return dict(self._data)
