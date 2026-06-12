"""Tracer — Distributed tracing for understanding decision flow."""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.observability.tracer")


class Span:
    def __init__(self, name: str, trace_id: str, parent_id: str | None = None):
        self.span_id = uuid.uuid4().hex[:8]
        self.trace_id = trace_id
        self.parent_id = parent_id
        self.name = name
        self.start_time = time.time()
        self.end_time: float | None = None
        self.attributes: dict[str, Any] = {}
        self.events: list[dict[str, Any]] = []

    def set_attribute(self, key: str, value: Any) -> None:
        self.attributes[key] = value

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append({"name": name, "attributes": attributes or {}, "timestamp": time.time()})

    def finish(self) -> None:
        self.end_time = time.time()

    @property
    def duration_ms(self) -> float:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return (time.time() - self.start_time) * 1000

    def to_dict(self) -> dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_id": self.parent_id,
            "name": self.name,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "events": self.events,
        }


class Tracer:
    """
    Distributed tracing for understanding decision flow.

    Trace: User request → Agent decision → Tool execution → Result
    """

    def __init__(self, storage_path: str = "spark_dev_memory/traces.jsonl") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._active_spans: dict[str, Span] = {}
        self._completed_traces: list[dict[str, Any]] = []

    def start_trace(self, name: str, attributes: dict[str, Any] | None = None) -> str:
        trace_id = uuid.uuid4().hex[:12]
        span = Span(name, trace_id)
        if attributes:
            span.attributes.update(attributes)
        self._active_spans[trace_id] = span
        return trace_id

    def start_span(self, trace_id: str, name: str, parent_id: str | None = None) -> str:
        span = Span(name, trace_id, parent_id)
        self._active_spans[f"{trace_id}:{span.span_id}"] = span
        return span.span_id

    def finish_span(self, trace_id: str, span_id: str, attributes: dict[str, Any] | None = None) -> None:
        key = f"{trace_id}:{span_id}"
        span = self._active_spans.get(key)
        if span:
            if attributes:
                span.attributes.update(attributes)
            span.finish()
            del self._active_spans[key]

    def finish_trace(self, trace_id: str) -> dict[str, Any] | None:
        span = self._active_spans.pop(trace_id, None)
        if span:
            span.finish()
            trace = span.to_dict()
            self._completed_traces.append(trace)
            if len(self._completed_traces) > 500:
                self._completed_traces = self._completed_traces[-500:]
            self._persist(trace)
            return trace
        return None

    def _persist(self, trace: dict[str, Any]) -> None:
        try:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(trace, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("Trace persist failed: %s", exc)

    def recent_traces(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._completed_traces[-limit:]

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        for t in self._completed_traces:
            if t.get("trace_id") == trace_id:
                return t
        return None
