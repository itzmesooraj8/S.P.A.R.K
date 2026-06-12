"""Procedural Memory — Learned skills and workflows."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class ProceduralMemory:
    """Stores learned procedures, workflows, and skills."""

    def __init__(self, storage_path: str = "spark_dev_memory/procedures.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._procedures: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._procedures = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception:
                self._procedures = {}

    def _save(self) -> None:
        self._path.write_text(json.dumps(self._procedures, indent=2, ensure_ascii=False), encoding="utf-8")

    def store(self, name: str, steps: list[dict[str, Any]], description: str = "") -> None:
        self._procedures[name] = {
            "description": description,
            "steps": steps,
            "created_at": time.time(),
            "last_used": 0.0,
            "use_count": 0,
        }
        self._save()

    def get(self, name: str) -> dict[str, Any] | None:
        proc = self._procedures.get(name)
        if proc:
            proc["last_used"] = time.time()
            proc["use_count"] = proc.get("use_count", 0) + 1
            self._save()
        return proc

    def list_all(self) -> list[str]:
        return list(self._procedures.keys())

    def delete(self, name: str) -> bool:
        if name in self._procedures:
            del self._procedures[name]
            self._save()
            return True
        return False
