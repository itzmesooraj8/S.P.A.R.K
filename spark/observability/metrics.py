"""Metrics Collector — Tracks system metrics for monitoring."""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.observability.metrics")


class MetricsCollector:
    """
    Tracks system metrics for monitoring.

    - Action counts
    - Success rates
    - Latency distributions
    - Error rates
    - Resource usage
    """

    def __init__(self, storage_path: str = "spark_dev_memory/metrics.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._counters: dict[str, int] = defaultdict(int)
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = defaultdict(list)
        self._timestamps: dict[str, float] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._counters = defaultdict(int, data.get("counters", {}))
                self._gauges = data.get("gauges", {})
                self._histograms = defaultdict(list, data.get("histograms", {}))
                self._timestamps = data.get("timestamps", {})
            except Exception:
                pass

    def _save(self) -> None:
        data = {
            "counters": dict(self._counters),
            "gauges": self._gauges,
            "histograms": {k: v[-100:] for k, v in self._histograms.items()},
            "timestamps": self._timestamps,
            "updated_at": time.time(),
        }
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def increment(self, name: str, value: int = 1) -> None:
        self._counters[name] += value
        self._timestamps[name] = time.time()
        self._save()

    def set_gauge(self, name: str, value: float) -> None:
        self._gauges[name] = value
        self._timestamps[name] = time.time()
        self._save()

    def record_histogram(self, name: str, value: float) -> None:
        self._histograms[name].append(value)
        if len(self._histograms[name]) > 1000:
            self._histograms[name] = self._histograms[name][-1000:]
        self._timestamps[name] = time.time()
        self._save()

    def record_action(self, action: str, success: bool, duration: float = 0.0) -> None:
        self.increment(f"action.{action}.total")
        if success:
            self.increment(f"action.{action}.success")
        else:
            self.increment(f"action.{action}.failure")
        if duration > 0:
            self.record_histogram(f"action.{action}.duration", duration)

    def record_agent(self, agent: str, action: str, duration: float = 0.0) -> None:
        self.increment(f"agent.{agent}.{action}")
        if duration > 0:
            self.record_histogram(f"agent.{agent}.duration", duration)

    def get_counter(self, name: str) -> int:
        return self._counters.get(name, 0)

    def get_gauge(self, name: str) -> float:
        return self._gauges.get(name, 0.0)

    def get_histogram_stats(self, name: str) -> dict[str, float]:
        values = self._histograms.get(name, [])
        if not values:
            return {"count": 0, "min": 0, "max": 0, "avg": 0, "p50": 0, "p95": 0, "p99": 0}
        sorted_vals = sorted(values)
        return {
            "count": len(values),
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "avg": sum(values) / len(values),
            "p50": sorted_vals[len(sorted_vals) // 2],
            "p95": sorted_vals[int(len(sorted_vals) * 0.95)],
            "p99": sorted_vals[int(len(sorted_vals) * 0.99)],
        }

    def snapshot(self) -> dict[str, Any]:
        return {
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: self.get_histogram_stats(k) for k in self._histograms},
        }
