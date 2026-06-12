"""Event Bus — Pub/Sub system for inter-module communication."""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine

logger = logging.getLogger("spark.core.events")


@dataclass(frozen=True)
class Event:
    """Immutable event payload."""
    topic: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = field(default_factory=time.time)


EventHandler = Callable[[Event], Coroutine[Any, Any, None]]


class EventBus:
    """Async publish-subscribe event bus."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[EventHandler]] = {}
        self._history: list[Event] = []
        self._max_history = 500

    def subscribe(self, topic: str, handler: EventHandler) -> None:
        self._handlers.setdefault(topic, []).append(handler)
        logger.debug("Subscribed to %s", topic)

    def unsubscribe(self, topic: str, handler: EventHandler) -> None:
        handlers = self._handlers.get(topic, [])
        if handler in handlers:
            handlers.remove(handler)

    async def publish(self, event: Event) -> None:
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        handlers = self._handlers.get(event.topic, [])
        wildcard = self._handlers.get("*", [])
        all_handlers = handlers + wildcard

        for handler in all_handlers:
            try:
                await handler(event)
            except Exception as exc:
                logger.error("Handler error on %s: %s", event.topic, exc)

    def emit(self, topic: str, payload: dict[str, Any] | None = None, source: str = "") -> None:
        """Synchronous convenience — schedules publish on running loop."""
        event = Event(topic=topic, payload=payload or {}, source=source)
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.publish(event))
        except RuntimeError:
            asyncio.run(self.publish(event))

    def recent(self, topic: str | None = None, limit: int = 20) -> list[Event]:
        events = self._history if topic is None else [e for e in self._history if e.topic == topic]
        return events[-limit:]
