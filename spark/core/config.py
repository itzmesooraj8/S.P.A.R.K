"""Configuration — Settings management."""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.core.config")

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = ROOT_DIR / "config.json"


class SparkConfig:
    """Hierarchical configuration with env override support."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._path = Path(config_path) if config_path else DEFAULT_CONFIG
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                self._data = json.loads(self._path.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Config load failed: %s", exc)
                self._data = {}

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        current = self._data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return default
            if current is None:
                return default
        return current

    def set(self, key: str, value: Any) -> None:
        parts = key.split(".")
        current = self._data
        for part in parts[:-1]:
            current = current.setdefault(part, {})
        current[parts[-1]] = value

    def env(self, key: str, default: str | None = None) -> str | None:
        return os.environ.get(key, default)

    @property
    def data(self) -> dict[str, Any]:
        return dict(self._data)
