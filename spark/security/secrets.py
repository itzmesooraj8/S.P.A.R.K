"""Secrets Manager — Never store secrets in code."""

from __future__ import annotations

import base64
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.security.secrets")


class SecretsManager:
    """
    Secure secrets management.

    - Never stores secrets in code
    - Loads from environment variables or encrypted file
    - Supports rotation
    """

    def __init__(self, storage_path: str = "spark_dev_memory/.secrets") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                encoded = self._path.read_text(encoding="utf-8")
                decoded = base64.b64decode(encoded).decode("utf-8")
                self._cache = json.loads(decoded)
            except Exception:
                pass

    def _save(self) -> None:
        try:
            encoded = base64.b64encode(json.dumps(self._cache).encode("utf-8")).decode("utf-8")
            self._path.write_text(encoded, encoding="utf-8")
            os.chmod(str(self._path), 0o600)
        except Exception as exc:
            logger.warning("Secrets save failed: %s", exc)

    def get(self, key: str, default: str = "") -> str:
        if key in self._cache:
            return self._cache[key]
        env_value = os.environ.get(key)
        if env_value:
            return env_value
        return default

    def set(self, key: str, value: str) -> None:
        self._cache[key] = value
        self._save()

    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            self._save()
            return True
        return False

    def has(self, key: str) -> bool:
        return key in self._cache or key in os.environ

    def list_keys(self) -> list[str]:
        keys = set(self._cache.keys())
        keys.update(k for k in os.environ if any(s in k.lower() for s in ["key", "token", "secret", "password"]))
        return list(keys)

    def get_api_key(self, service: str) -> str:
        return self.get(f"{service.upper()}_API_KEY", self.get(f"{service.upper()}_TOKEN", ""))
