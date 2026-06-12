"""Registry — Component registration and discovery."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("spark.core.registry")


class Registry:
    """Central registry for named components and services."""

    def __init__(self) -> None:
        self._services: dict[str, Any] = {}
        self._factories: dict[str, Any] = {}

    def register(self, name: str, instance: Any) -> None:
        self._services[name] = instance
        logger.debug("Registered service: %s", name)

    def register_factory(self, name: str, factory: Any) -> None:
        self._factories[name] = factory

    def get(self, name: str) -> Any:
        if name in self._services:
            return self._services[name]
        if name in self._factories:
            instance = self._factories[name]()
            self._services[name] = instance
            return instance
        raise KeyError(f"Service not found: {name}")

    def has(self, name: str) -> bool:
        return name in self._services or name in self._factories

    def list_all(self) -> list[str]:
        return list(set(list(self._services.keys()) + list(self._factories.keys())))
