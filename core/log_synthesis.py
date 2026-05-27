"""S.P.A.R.K Automated Log Synthesis & De-Noising.

Compresses repetitive agent telemetry into dense JSON records and persists the
result into monthly SQLite partitions to keep diagnostic loops lightweight.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from threading import RLock
from typing import Any, AsyncIterable, Dict, List, Optional

from core.db_partitioner import DatabasePartitioner

logger = logging.getLogger("SPARK_LOG_SYNTHESIS")

class LogSynthesizer:
    """Filters log streams, compressing repetitive boilerplate messages to structured JSON summaries."""

    def __init__(self, frequency_window: int = 10, partitioner: Optional[DatabasePartitioner] = None):
        self.frequency_window = frequency_window
        self.partitioner = partitioner or DatabasePartitioner()
        self._lock = RLock()
        # Regex tokens mapping raw logs to normalized semantic buckets
        self.rules: Dict[str, re.Pattern] = {
            "heartbeat": re.compile(r"(heartbeat|ping|pulse|tick|alive)", re.IGNORECASE),
            "db_query": re.compile(r"(select|insert|update|delete|chromadb|collection|query|sqlite)", re.IGNORECASE),
            "network_poll": re.compile(r"(connection|socket|ip|port|host|arp|dns|http|request)", re.IGNORECASE),
            "gui_action": re.compile(r"(click|mouse|hover|pyautogui|coordinate|screen|grab)", re.IGNORECASE),
            "llm_inference": re.compile(r"(ollama|groq|token|inference|llm|chat|completion|reply)", re.IGNORECASE),
            "error_state": re.compile(r"(error|failed|exception|traceback|timeout|overflow|permission denied)", re.IGNORECASE),
        }
        self.history: List[Dict[str, Any]] = []

    @staticmethod
    def _extract_timestamp_and_origin(line: str) -> tuple[str, str]:
        timestamp_match = re.match(r"^(?P<timestamp>\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*[-|:]?\s*(?P<rest>.*)$", line)
        if timestamp_match:
            return timestamp_match.group("timestamp"), timestamp_match.group("rest")
        return datetime.utcnow().isoformat(timespec="seconds"), line

    def _categorize(self, line: str) -> str:
        matched_category = "general_runtime"
        for category, pattern in self.rules.items():
            if pattern.search(line):
                matched_category = category
                break
        return matched_category

    def _build_entry(self, category: str, raw_lines: List[str]) -> Dict[str, Any]:
        first_timestamp, first_body = self._extract_timestamp_and_origin(raw_lines[0])
        origin = first_body.split(" - ", 1)[0].strip() if " - " in first_body else category
        combined = " ".join(raw_lines)
        error_state = bool(self.rules["error_state"].search(combined))

        return {
            "timestamp": first_timestamp,
            "origin": origin,
            "error_state": error_state,
            "category": category,
            "raw_occurrences": len(raw_lines),
            "sample_log": raw_lines[0][:200],
            "compressed_summary": f"Collapsed {len(raw_lines)} {category} log lines from {origin}.",
            "compressed_field_count": 6,
        }

    def _persist_entries(self, entries: List[Dict[str, Any]]) -> None:
        for entry in entries:
            try:
                self.partitioner.log_runtime_event(
                    "ERROR" if entry["error_state"] else "INFO",
                    entry["category"],
                    json.dumps(entry, ensure_ascii=True),
                )
            except Exception as exc:
                logger.debug(f"Partition persistence skipped: {exc}")

    def _flush_group(self, category: str, raw_lines: List[str]) -> Dict[str, Any]:
        entry = self._build_entry(category, raw_lines)
        self.history.append(entry)
        return entry

    def synthesize_stream(self, raw_lines: List[str]) -> str:
        """Parses a block of log lines and outputs a compressed JSON summary array."""
        synthesized: List[Dict[str, Any]] = []

        with self._lock:
            current_category: Optional[str] = None
            current_group: List[str] = []

            for raw_line in raw_lines:
                line = raw_line.strip()
                if not line:
                    continue

                matched_category = self._categorize(line)
                if matched_category == current_category:
                    current_group.append(line)
                    continue

                if current_category and current_group:
                    synthesized.append(self._flush_group(current_category, current_group))

                current_category = matched_category
                current_group = [line]

            if current_category and current_group:
                synthesized.append(self._flush_group(current_category, current_group))

            self._persist_entries(synthesized)

        return json.dumps(synthesized, indent=2)

    async def ingest_async(self, log_stream: AsyncIterable[str]) -> str:
        """Continuously ingest asynchronous log lines and return compressed JSON."""
        buffer: List[str] = []
        async for line in log_stream:
            if line:
                buffer.append(line)
            if len(buffer) >= self.frequency_window:
                break
        return self.synthesize_stream(buffer)

    def ingest_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Accept a single line and update local history with immediate compression."""
        if not line:
            return None
        return json.loads(self.synthesize_stream([line]))[0]

    def get_high_density_summary(self) -> Dict[str, Any]:
        """Provides an aggregated count of all logs processed by category."""
        counts: Dict[str, int] = {}
        for entry in self.history:
            cat = entry["category"]
            counts[cat] = counts.get(cat, 0) + int(entry["raw_occurrences"])

        return {
            "total_raw_processed": sum(counts.values()),
            "category_aggregations": counts,
            "status": "de-noised nominal log state",
        }
