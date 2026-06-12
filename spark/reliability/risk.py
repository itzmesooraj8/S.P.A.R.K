"""Risk Engine — Evaluates risk before every action."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger("spark.reliability.risk")


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskAssessment:
    def __init__(self, level: RiskLevel, score: float, requires_confirmation: bool, reason: str):
        self.level = level
        self.score = score
        self.requires_confirmation = requires_confirmation
        self.reason = reason

    def to_dict(self) -> dict[str, Any]:
        return {"level": self.level.value, "score": self.score, "requires_confirmation": self.requires_confirmation, "reason": self.reason}

    def __bool__(self) -> bool:
        return self.level != RiskLevel.CRITICAL


class RiskEngine:
    """
    Evaluates risk before every action.

    Delete files? Risk = High → Ask user
    Open browser? Risk = Low → Proceed
    Send email? Risk = Medium → Ask user
    Spend money? Risk = Critical → Block

    This becomes critical once autonomy increases.
    """

    def __init__(self) -> None:
        self._rules: dict[str, dict[str, Any]] = {
            "delete_file": {"level": RiskLevel.HIGH, "score": 0.8, "confirmation": True},
            "write_file": {"level": RiskLevel.MEDIUM, "score": 0.5, "confirmation": False},
            "execute_shell": {"level": RiskLevel.HIGH, "score": 0.9, "confirmation": True},
            "open_browser": {"level": RiskLevel.LOW, "score": 0.2, "confirmation": False},
            "take_screenshot": {"level": RiskLevel.LOW, "score": 0.1, "confirmation": False},
            "send_email": {"level": RiskLevel.MEDIUM, "score": 0.6, "confirmation": True},
            "web_search": {"level": RiskLevel.LOW, "score": 0.1, "confirmation": False},
            "type_text": {"level": RiskLevel.MEDIUM, "score": 0.4, "confirmation": False},
            "open_application": {"level": RiskLevel.MEDIUM, "score": 0.3, "confirmation": False},
            "spend_money": {"level": RiskLevel.CRITICAL, "score": 1.0, "confirmation": True},
            "modify_system": {"level": RiskLevel.CRITICAL, "score": 0.95, "confirmation": True},
            "read_clipboard": {"level": RiskLevel.LOW, "score": 0.1, "confirmation": False},
            "write_clipboard": {"level": RiskLevel.LOW, "score": 0.2, "confirmation": False},
            "file_search": {"level": RiskLevel.LOW, "score": 0.1, "confirmation": False},
            "system_monitor": {"level": RiskLevel.LOW, "score": 0.05, "confirmation": False},
        }

    def assess(self, action: str, context: dict[str, Any] | None = None) -> RiskAssessment:
        rule = self._rules.get(action, {"level": RiskLevel.MEDIUM, "score": 0.5, "confirmation": True})
        level = RiskLevel(rule["level"])
        score = rule["score"]
        needs_confirm = rule["confirmation"]

        ctx = context or {}
        if ctx.get("repeated_failure"):
            score = min(score + 0.2, 1.0)
            if score > 0.7:
                level = RiskLevel.HIGH
                needs_confirm = True

        if ctx.get("user_recently_denied"):
            score = min(score + 0.3, 1.0)
            level = RiskLevel.HIGH
            needs_confirm = True

        return RiskAssessment(
            level=level,
            score=score,
            requires_confirmation=needs_confirm,
            reason=f"Action '{action}' assessed as {level.value} risk (score: {score:.2f})",
        )

    def add_rule(self, action: str, level: RiskLevel, score: float, confirmation: bool) -> None:
        self._rules[action] = {"level": level.value, "score": score, "confirmation": confirmation}

    def get_rules(self) -> dict[str, Any]:
        return dict(self._rules)
