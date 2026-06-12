"""Decision Log — Records why SPARK did what it did."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from dataclasses import dataclass, field


@dataclass
class Decision:
    """A single recorded decision."""
    action: str
    reason: str
    context: dict[str, Any] = field(default_factory=dict)
    alternatives: list[str] = field(default_factory=list)
    confidence: float = 0.5
    outcome: str = "pending"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "context": self.context,
            "alternatives": self.alternatives,
            "confidence": self.confidence,
            "outcome": self.outcome,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class DecisionLog:
    """
    Persistent decision log for debugging and learning.

    Every decision SPARK makes is recorded with:
    - What action was taken
    - Why it was chosen
    - What alternatives existed
    - What the confidence was
    - What the outcome was
    """

    def __init__(self, storage_path: str = "spark_dev_memory/decisions.jsonl") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._recent: list[Decision] = []
        self._max_recent = 100

    def record(self, decision: Decision) -> None:
        self._recent.append(decision)
        if len(self._recent) > self._max_recent:
            self._recent = self._recent[-self._max_recent:]

        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(decision.to_dict(), ensure_ascii=False) + "\n")

    def log(self, action: str, reason: str, context: dict[str, Any] | None = None, alternatives: list[str] | None = None, confidence: float = 0.5) -> Decision:
        decision = Decision(
            action=action,
            reason=reason,
            context=context or {},
            alternatives=alternatives or [],
            confidence=confidence,
        )
        self.record(decision)
        return decision

    def record_outcome(self, decision: Decision, outcome: str, success: bool) -> None:
        decision.outcome = outcome
        decision.metadata["success"] = success
        self.record(decision)

    def recent(self, limit: int = 20) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._recent[-limit:]]

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        all_decisions = self._load_all()
        query_lower = query.lower()
        matches = [d for d in all_decisions if query_lower in d.get("action", "").lower() or query_lower in d.get("reason", "").lower()]
        return matches[-limit:]

    def _load_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        decisions = []
        for line in self._path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                try:
                    decisions.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return decisions

    def stats(self) -> dict[str, Any]:
        all_d = self._load_all()
        total = len(all_d)
        successful = sum(1 for d in all_d if d.get("metadata", {}).get("success"))
        return {
            "total_decisions": total,
            "successful": successful,
            "success_rate": successful / total if total > 0 else 0.0,
        }

    def clear(self) -> None:
        self._recent.clear()
        if self._path.exists():
            self._path.write_text("", encoding="utf-8")
