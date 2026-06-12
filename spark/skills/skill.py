"""Skill — Reusable capability that can be composed into workflows."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger("spark.skills")


@dataclass
class SkillStep:
    name: str
    action: str
    params: dict[str, Any] = field(default_factory=dict)
    expected_output: str = ""
    on_failure: str = "abort"


@dataclass
class SkillResult:
    success: bool
    output: Any = None
    error: str = ""
    steps_completed: int = 0
    duration_ms: float = 0.0


class Skill:
    """
    A reusable skill that SPARK can learn, store, and execute.

    Example:
        Skill(
            name="create_website",
            description="Create a website from scratch",
            steps=[
                SkillStep("plan", "reason", {"question": "What kind of website?"}),
                SkillStep("search", "web_search", {"query": "best practices"}),
                SkillStep("create", "file_write", {"path": "index.html"}),
            ],
            tags=["web", "creation"],
        )
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        steps: list[SkillStep] | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ):
        self.name = name
        self.description = description
        self.steps = steps or []
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = time.time()
        self.last_used: float = 0.0
        self.use_count: int = 0
        self.success_rate: float = 1.0
        self._total_runs = 0
        self._successes = 0

    def execute_step(self, step: SkillStep, executor: Callable[[str, dict], Coroutine[Any, Any, Any]]) -> dict[str, Any]:
        """Execute a single step."""
        return {"step": step.name, "action": step.action, "params": step.params}

    def record_use(self, success: bool) -> None:
        self.use_count += 1
        self._total_runs += 1
        self.last_used = time.time()
        if success:
            self._successes += 1
        self.success_rate = self._successes / self._total_runs if self._total_runs > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "steps": [{"name": s.name, "action": s.action, "params": s.params} for s in self.steps],
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "use_count": self.use_count,
            "success_rate": self.success_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Skill:
        steps = [SkillStep(**s) for s in data.get("steps", [])]
        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            steps=steps,
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
        )

    def __repr__(self) -> str:
        return f"<Skill name={self.name} steps={len(self.steps)} uses={self.use_count}>"


class SkillRegistry:
    """Manages all learned skills."""

    def __init__(self) -> None:
        self._skills: dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        self._skills[skill.name] = skill
        logger.info("Skill registered: %s", skill.name)

    def get(self, name: str) -> Skill | None:
        return self._skills.get(name)

    def has(self, name: str) -> bool:
        return name in self._skills

    def list_all(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._skills.values()]

    def find_by_tag(self, tag: str) -> list[Skill]:
        return [s for s in self._skills.values() if tag in s.tags]

    def find_best(self, query: str) -> Skill | None:
        query_lower = query.lower()
        best = None
        best_score = 0.0
        for skill in self._skills.values():
            score = 0.0
            if query_lower in skill.name.lower():
                score += 2.0
            if query_lower in skill.description.lower():
                score += 1.0
            for tag in skill.tags:
                if query_lower in tag.lower():
                    score += 0.5
            if score > best_score:
                best_score = score
                best = skill
        return best

    def learn_from_action(self, name: str, steps: list[dict[str, Any]], description: str = "", tags: list[str] | None = None) -> Skill:
        """Learn a new skill from observed actions."""
        skill_steps = [SkillStep(name=s.get("name", ""), action=s.get("action", ""), params=s.get("params", {})) for s in steps]
        skill = Skill(name=name, description=description, steps=skill_steps, tags=tags or [])
        self.register(skill)
        return skill

    def remove(self, name: str) -> bool:
        if name in self._skills:
            del self._skills[name]
            return True
        return False

    def count(self) -> int:
        return len(self._skills)
