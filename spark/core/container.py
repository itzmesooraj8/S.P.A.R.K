"""Dependency Injection Container."""

from __future__ import annotations

import logging
from typing import Any, TypeVar, Type

from spark.core.events import EventBus
from spark.core.state import StateManager
from spark.core.config import SparkConfig
from spark.core.registry import Registry

logger = logging.getLogger("spark.core.container")

T = TypeVar("T")


class Container:
    """Central DI container — wires all core services together."""

    _instance: Container | None = None

    def __init__(self) -> None:
        self.events = EventBus()
        self.state = StateManager()
        self.config = SparkConfig()
        self.registry = Registry()
        self._initialized = False

    @classmethod
    def get_instance(cls) -> Container:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None

    def initialize(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        logger.info("SPARK Container initialized")

    def register(self, name: str, instance: Any) -> None:
        self.registry.register(name, instance)

    def resolve(self, name: str) -> Any:
        return self.registry.get(name)
