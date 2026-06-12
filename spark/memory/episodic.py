"""Episodic Memory — Conversation history and events."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class EpisodicMemory:
    """Stores conversation turns and events as episodic memories."""

    def __init__(self, storage_path: str = "spark_dev_memory/episodes.jsonl") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        entry = {
            "role": role,
            "content": content,
            "timestamp": time.time(),
            "metadata": metadata or {},
        }
        with self._path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def recent(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        lines = self._path.read_text(encoding="utf-8").splitlines()
        episodes = []
        for line in lines[-limit:]:
            line = line.strip()
            if line:
                try:
                    episodes.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return episodes

    def search(self, query: str, limit: int = 10) -> list[dict[str, Any]]:
        episodes = self.recent(limit=500)
        query_lower = query.lower()
        matches = [ep for ep in episodes if query_lower in ep.get("content", "").lower()]
        return matches[-limit:]

    def count(self) -> int:
        if not self._path.exists():
            return 0
        return len(self._path.read_text(encoding="utf-8").splitlines())

    def clear(self) -> None:
        if self._path.exists():
            self._path.write_text("", encoding="utf-8")
