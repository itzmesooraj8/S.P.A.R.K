"""Advanced Learning Engine — Strategy selection, evolution, and retirement."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.learning.advanced")


class Strategy:
    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.uses = 0
        self.successes = 0
        self.failures = 0
        self.avg_duration = 0.0
        self.last_used = 0.0
        self.first_used = time.time()
        self.retired = False
        self.retired_at: float | None = None
        self.retired_reason = ""
        self.variants: list[dict[str, Any]] = []

    @property
    def success_rate(self) -> float:
        return self.successes / self.uses if self.uses > 0 else 0.0

    @property
    def is_reliable(self) -> bool:
        return self.uses >= 5 and self.success_rate > 0.7

    @property
    def should_retire(self) -> bool:
        return self.uses >= 10 and self.success_rate < 0.3

    def record(self, success: bool, duration: float = 0.0) -> None:
        self.uses += 1
        if success:
            self.successes += 1
        else:
            self.failures += 1
        if duration > 0:
            self.avg_duration = (self.avg_duration * (self.uses - 1) + duration) / self.uses
        self.last_used = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "category": self.category,
            "uses": self.uses,
            "successes": self.successes,
            "failures": self.failures,
            "success_rate": self.success_rate,
            "avg_duration": self.avg_duration,
            "is_reliable": self.is_reliable,
            "retired": self.retired,
            "retired_reason": self.retired_reason,
        }


class AdvancedLearningEngine:
    """
    Strategy selection, evolution, and retirement.

    Not just tracking success rates.
    Actively managing strategy lifecycle.

    - Selects best strategy for each task
    - Evolves strategies based on outcomes
    - Retires poor strategies automatically
    - Learns from failures to create new approaches
    """

    def __init__(self, storage_path: str = "spark_dev_memory/advanced_learning.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._strategies: dict[str, Strategy] = {}
        self._task_history: list[dict[str, Any]] = []
        self._evolution_log: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                for key, s_data in data.get("strategies", {}).items():
                    s = Strategy(s_data["name"], s_data["category"])
                    s.uses = s_data.get("uses", 0)
                    s.successes = s_data.get("successes", 0)
                    s.failures = s_data.get("failures", 0)
                    s.avg_duration = s_data.get("avg_duration", 0.0)
                    s.last_used = s_data.get("last_used", 0.0)
                    s.first_used = s_data.get("first_used", time.time())
                    s.retired = s_data.get("retired", False)
                    s.retired_at = s_data.get("retired_at")
                    s.retired_reason = s_data.get("retired_reason", "")
                    self._strategies[key] = s
                self._task_history = data.get("task_history", [])[-200:]
                self._evolution_log = data.get("evolution_log", [])[-100:]
            except Exception:
                pass

    def _save(self) -> None:
        data = {
            "strategies": {k: s.to_dict() for k, s in self._strategies.items()},
            "task_history": self._task_history[-200:],
            "evolution_log": self._evolution_log[-100:],
            "updated_at": time.time(),
        }
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def select_strategy(self, category: str) -> str | None:
        """Select the best strategy for a category."""
        candidates = [
            s for s in self._strategies.values()
            if s.category == category and not s.retired and s.uses >= 3
        ]
        if not candidates:
            return None
        candidates.sort(key=lambda s: s.success_rate, reverse=True)
        return candidates[0].name

    def record_outcome(self, strategy_name: str, category: str, success: bool, duration: float = 0.0) -> None:
        key = f"{category}:{strategy_name}"
        if key not in self._strategies:
            self._strategies[key] = Strategy(strategy_name, category)
        self._strategies[key].record(success, duration)

        self._task_history.append({
            "strategy": strategy_name,
            "category": category,
            "success": success,
            "duration": duration,
            "timestamp": time.time(),
        })

        self._check_retirement(self._strategies[key])
        self._check_evolution(category)
        self._save()

    def _check_retirement(self, strategy: Strategy) -> None:
        if strategy.should_retire and not strategy.retired:
            strategy.retired = True
            strategy.retired_at = time.time()
            strategy.retired_reason = f"Success rate {strategy.success_rate:.0%} below threshold after {strategy.uses} uses"
            self._evolution_log.append({
                "action": "retire",
                "strategy": strategy.name,
                "category": strategy.category,
                "reason": strategy.retired_reason,
                "timestamp": time.time(),
            })
            logger.info("Strategy retired: %s (%s)", strategy.name, strategy.retired_reason)

    def _check_evolution(self, category: str) -> None:
        strategies = [s for s in self._strategies.values() if s.category == category and not s.retired]
        if len(strategies) < 2:
            return
        strategies.sort(key=lambda s: s.success_rate, reverse=True)
        best = strategies[0]
        worst = strategies[-1]
        if best.success_rate - worst.success_rate > 0.4 and worst.uses >= 5:
            worst.retired = True
            worst.retired_at = time.time()
            worst.retired_reason = f"Evolution: {best.name} ({best.success_rate:.0%}) significantly outperforms"
            self._evolution_log.append({
                "action": "evolution_retire",
                "retired": worst.name,
                "preferred": best.name,
                "category": category,
                "timestamp": time.time(),
            })

    def get_recommendations(self, category: str) -> list[dict[str, Any]]:
        strategies = [
            s for s in self._strategies.values()
            if s.category == category and not s.retired
        ]
        strategies.sort(key=lambda s: s.success_rate, reverse=True)
        return [
            {
                "name": s.name,
                "success_rate": s.success_rate,
                "uses": s.uses,
                "recommendation": "prefer" if s.is_reliable else "use_with_caution",
            }
            for s in strategies
        ]

    def get_retired_strategies(self) -> list[dict[str, Any]]:
        return [s.to_dict() for s in self._strategies.values() if s.retired]

    def get_evolution_log(self) -> list[dict[str, Any]]:
        return self._evolution_log

    def stats(self) -> dict[str, Any]:
        active = [s for s in self._strategies.values() if not s.retired]
        retired = [s for s in self._strategies.values() if s.retired]
        return {
            "active_strategies": len(active),
            "retired_strategies": len(retired),
            "avg_success_rate": sum(s.success_rate for s in active) / len(active) if active else 0.0,
            "total_tasks": len(self._task_history),
        }
