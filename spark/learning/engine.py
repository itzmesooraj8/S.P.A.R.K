"""Learning Engine — Continuous self-improvement through observation."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.learning.engine")


class StrategyRecord:
    def __init__(self, name: str, category: str, success: bool, duration: float = 0.0, context: dict[str, Any] | None = None):
        self.name = name
        self.category = category
        self.success = success
        self.duration = duration
        self.context = context or {}
        self.timestamp = time.time()


class LearningEngine:
    """
    Continuous self-improvement through observation.

    Tracks all strategy outcomes.
    Learns which strategies work best.
    Automatically prefers successful strategies.
    Replaces poor strategies.

    Example:
    - Playwright succeeded 95% → Use automatically
    - Selenium succeeded 60% → Avoid or retry differently
    """

    def __init__(self, storage_path: str = "spark_dev_memory/learning.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._strategies: dict[str, dict[str, Any]] = {}
        self._history: list[dict[str, Any]] = []
        self._max_history = 500
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._strategies = data.get("strategies", {})
                self._history = data.get("history", [])[-self._max_history:]
            except Exception:
                pass

    def _save(self) -> None:
        data = {"strategies": self._strategies, "history": self._history[-self._max_history:]}
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def record(self, strategy: str, category: str, success: bool, duration: float = 0.0, context: dict[str, Any] | None = None) -> None:
        record = StrategyRecord(strategy, category, success, duration, context)
        entry = {
            "strategy": strategy,
            "category": category,
            "success": success,
            "duration": duration,
            "timestamp": time.time(),
        }
        self._history.append(entry)

        key = f"{category}:{strategy}"
        if key not in self._strategies:
            self._strategies[key] = {
                "name": strategy,
                "category": category,
                "uses": 0,
                "successes": 0,
                "failures": 0,
                "success_rate": 0.0,
                "avg_duration": 0.0,
                "last_used": 0.0,
                "first_used": time.time(),
            }

        s = self._strategies[key]
        s["uses"] += 1
        if success:
            s["successes"] += 1
        else:
            s["failures"] += 1
        s["success_rate"] = s["successes"] / s["uses"] if s["uses"] > 0 else 0.0
        if duration > 0:
            s["avg_duration"] = (s["avg_duration"] * (s["uses"] - 1) + duration) / s["uses"]
        s["last_used"] = time.time()

        self._save()
        logger.debug("Recorded: %s (%s) = %s (rate: %.0f%%)", strategy, category, "success" if success else "fail", s["success_rate"] * 100)

    def get_best_strategy(self, category: str) -> str | None:
        best = None
        best_rate = 0.0
        for key, stats in self._strategies.items():
            if stats["category"] == category and stats["uses"] >= 3:
                if stats["success_rate"] > best_rate:
                    best_rate = stats["success_rate"]
                    best = stats["name"]
        return best

    def get_worst_strategy(self, category: str) -> str | None:
        worst = None
        worst_rate = 1.0
        for key, stats in self._strategies.items():
            if stats["category"] == category and stats["uses"] >= 3:
                if stats["success_rate"] < worst_rate:
                    worst_rate = stats["success_rate"]
                    worst = stats["name"]
        return worst

    def should_use_strategy(self, strategy: str, category: str) -> bool:
        best = self.get_best_strategy(category)
        if best and best != strategy:
            return False
        key = f"{category}:{strategy}"
        stats = self._strategies.get(key)
        if stats and stats["uses"] >= 5 and stats["success_rate"] < 0.4:
            return False
        return True

    def get_recommendations(self, category: str) -> list[dict[str, Any]]:
        strategies = []
        for key, stats in self._strategies.items():
            if stats["category"] == category and stats["uses"] >= 2:
                strategies.append({
                    "name": stats["name"],
                    "success_rate": stats["success_rate"],
                    "uses": stats["uses"],
                    "avg_duration": stats["avg_duration"],
                    "recommendation": "prefer" if stats["success_rate"] > 0.8 else "avoid" if stats["success_rate"] < 0.4 else "use_with_caution",
                })
        strategies.sort(key=lambda x: x["success_rate"], reverse=True)
        return strategies

    def learn_from_task(self, task: str, strategies_tried: list[str], final_strategy: str, success: bool) -> None:
        for strategy in strategies_tried:
            self.record(strategy, task, strategy == final_strategy and success)
        if not success:
            logger.info("Task '%s' failed with all strategies", task)

    def get_stats(self) -> dict[str, Any]:
        total = len(self._strategies)
        avg_rate = sum(s["success_rate"] for s in self._strategies.values()) / total if total > 0 else 0.0
        return {
            "total_strategies": total,
            "avg_success_rate": avg_rate,
            "total_records": len(self._history),
            "best_strategies": [
                {"name": s["name"], "category": s["category"], "rate": s["success_rate"]}
                for s in sorted(self._strategies.values(), key=lambda x: x["success_rate"], reverse=True)[:5]
            ],
        }

    def snapshot(self) -> dict[str, Any]:
        return {"strategies": dict(self._strategies), "stats": self.get_stats()}
