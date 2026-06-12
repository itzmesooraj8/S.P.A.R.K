"""Base Integration — Abstract adapter for external services."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Integration(ABC):
    """Abstract base for external service integrations."""

    def __init__(self, name: str, config: dict[str, Any] | None = None):
        self.name = name
        self.config = config or {}
        self._connected = False

    @abstractmethod
    async def connect(self) -> bool:
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        ...

    @abstractmethod
    async def send(self, message: str, **kwargs: Any) -> dict[str, Any]:
        ...

    @abstractmethod
    async def receive(self) -> dict[str, Any] | None:
        ...

    @property
    def is_connected(self) -> bool:
        return self._connected

    def info(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "connected": self._connected,
            "config_keys": list(self.config.keys()),
        }
