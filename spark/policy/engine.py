"""Policy Engine — Constitution for autonomous actions."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger("spark.policy.engine")


class Verdict(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"
    LOG = "log"


@dataclass
class PolicyRule:
    name: str
    description: str
    check: Callable[[dict[str, Any]], bool]
    verdict: Verdict = Verdict.ALLOW
    risk_level: str = "low"
    enabled: bool = True


@dataclass
class PolicyResult:
    allowed: bool
    verdict: Verdict
    reason: str
    rule_name: str = ""
    risk_level: str = "low"
    requires_confirmation: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "verdict": self.verdict.value,
            "reason": self.reason,
            "rule_name": self.rule_name,
            "risk_level": self.risk_level,
            "requires_confirmation": self.requires_confirmation,
        }


class PolicyEngine:
    """
    Constitution for autonomous actions.

    Every action passes policy.evaluate() before execution.
    Similar to OPA/Guardrails/Rego.
    """

    def __init__(self) -> None:
        self._rules: list[PolicyRule] = []
        self._log: list[dict[str, Any]] = []
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(PolicyRule(
            name="no_secrets_in_llm",
            description="Never allow .env, secrets, tokens to enter LLM context",
            check=lambda ctx: not self._contains_secrets(ctx.get("input", "")),
            verdict=Verdict.DENY,
            risk_level="critical",
        ))

        self.register(PolicyRule(
            name="no_delete_without_confirmation",
            description="Delete operations require user confirmation",
            check=lambda ctx: "delete" not in ctx.get("action", "").lower(),
            verdict=Verdict.CONFIRM,
            risk_level="high",
        ))

        self.register(PolicyRule(
            name="no_execute_shell_without_confirmation",
            description="Shell execution requires user confirmation",
            check=lambda ctx: ctx.get("action", "") != "execute_shell",
            verdict=Verdict.CONFIRM,
            risk_level="high",
        ))

        self.register(PolicyRule(
            name="autonomous_actions_need_budget",
            description="Autonomous actions must have a confidence budget",
            check=lambda ctx: ctx.get("source") != "autonomous" or ctx.get("confidence", 0) >= 0.7,
            verdict=Verdict.DENY,
            risk_level="medium",
        ))

        self.register(PolicyRule(
            name="rate_limit_autonomous",
            description="Limit autonomous actions to 10 per hour",
            check=lambda ctx: ctx.get("source") != "autonomous" or self._check_rate_limit(),
            verdict=Verdict.DENY,
            risk_level="medium",
        ))

    def register(self, rule: PolicyRule) -> None:
        self._rules.append(rule)

    def evaluate(self, context: dict[str, Any]) -> PolicyResult:
        """Evaluate all rules against the context."""
        for rule in self._rules:
            if not rule.enabled:
                continue

            try:
                passed = rule.check(context)
            except Exception as exc:
                logger.error("Rule %s check failed: %s", rule.name, exc)
                continue

            if not passed:
                result = PolicyResult(
                    allowed=rule.verdict == Verdict.ALLOW,
                    verdict=rule.verdict,
                    reason=f"Rule '{rule.name}' failed: {rule.description}",
                    rule_name=rule.name,
                    risk_level=rule.risk_level,
                    requires_confirmation=rule.verdict == Verdict.CONFIRM,
                )
                self._log_event(context, result)
                return result

        result = PolicyResult(
            allowed=True,
            verdict=Verdict.ALLOW,
            reason="All rules passed",
        )
        self._log_event(context, result)
        return result

    def _contains_secrets(self, text: str) -> bool:
        secret_patterns = [".env", "secret", "token", "password", "api_key", "ssh", "private_key"]
        text_lower = text.lower()
        return any(p in text_lower for p in secret_patterns)

    def _check_rate_limit(self) -> bool:
        now = time.time()
        hour_ago = now - 3600
        recent = [e for e in self._log if e.get("timestamp", 0) > hour_ago and e.get("source") == "autonomous"]
        return len(recent) < 10

    def _log_event(self, context: dict[str, Any], result: PolicyResult) -> None:
        entry = {
            "action": context.get("action", "unknown"),
            "source": context.get("source", "unknown"),
            "verdict": result.verdict.value,
            "rule": result.rule_name,
            "risk_level": result.risk_level,
            "timestamp": time.time(),
        }
        self._log.append(entry)
        if len(self._log) > 500:
            self._log = self._log[-500:]

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._log[-limit:]

    def stats(self) -> dict[str, Any]:
        total = len(self._log)
        denied = sum(1 for e in self._log if e.get("verdict") == "deny")
        confirmed = sum(1 for e in self._log if e.get("verdict") == "confirm")
        return {
            "total_evaluations": total,
            "denied": denied,
            "confirmed": confirmed,
            "allowed": total - denied - confirmed,
            "rules": len(self._rules),
        }
