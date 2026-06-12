"""Awareness Bus — Publishes awareness events to the system.

Observer → Event Bus → Awareness Model → Memory → Goal Engine

This creates system-wide intelligence.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Coroutine

from spark.core.events import EventBus, Event

logger = logging.getLogger("spark.awareness.bus")


class AwarenessEvent:
    """Represents a change in the environment."""

    def __init__(self, event_type: str, data: dict[str, Any], source: str = "observer"):
        self.event_type = event_type
        self.data = data
        self.source = source
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp,
        }


AwarenessHandler = Callable[[AwarenessEvent], Coroutine[Any, Any, None]]


class AwarenessBus:
    """
    Continuous awareness publisher.

    Receives raw observations from ObserverAgent,
    normalizes them into AwarenessEvents,
    and publishes to the event bus for system-wide consumption.
    """

    def __init__(self, event_bus: EventBus) -> None:
        self._event_bus = event_bus
        self._handlers: dict[str, list[AwarenessHandler]] = {}
        self._recent_events: list[AwarenessEvent] = []
        self._max_recent = 100
        self._last_observation: dict[str, Any] = {}
        self._change_detectors: dict[str, Callable[[dict[str, Any], dict[str, Any]], bool]] = {}

    def on(self, event_type: str, handler: AwarenessHandler) -> None:
        self._handlers.setdefault(event_type, []).append(handler)

    async def publish(self, event: AwarenessEvent) -> None:
        self._recent_events.append(event)
        if len(self._recent_events) > self._max_recent:
            self._recent_events = self._recent_events[-self._max_recent:]

        handlers = self._handlers.get(event.event_type, [])
        wildcard = self._handlers.get("*", [])
        for handler in handlers + wildcard:
            try:
                await handler(event)
            except Exception as exc:
                logger.error("Awareness handler error: %s", exc)

        await self._event_bus.publish(Event(
            topic=f"awareness.{event.event_type}",
            payload=event.data,
            source=event.source,
        ))

    async def process_observation(self, observation: dict[str, Any]) -> list[AwarenessEvent]:
        """Compare new observation with last, detect changes, publish events."""
        events = []
        previous = self._last_observation
        self._last_observation = observation

        detectors = {
            "screen": self._detect_screen_change,
            "application": self._detect_app_change,
            "user": self._detect_user_change,
            "environment": self._detect_env_change,
        }

        for key, detector in detectors.items():
            if key in observation:
                changed = detector(previous.get(key, {}), observation[key])
                if changed:
                    event = AwarenessEvent(
                        event_type=f"{key}_changed",
                        data={"previous": previous.get(key, {}), "current": observation[key]},
                    )
                    events.append(event)
                    await self.publish(event)

        if events:
            summary_event = AwarenessEvent(
                event_type="environment_update",
                data={"changes": [e.event_type for e in events], "observation": observation},
            )
            events.append(summary_event)
            await self.publish(summary_event)

        return events

    def _detect_screen_change(self, old: dict, new: dict) -> bool:
        return old.get("active_window") != new.get("active_window")

    def _detect_app_change(self, old: dict, new: dict) -> bool:
        return old.get("focused") != new.get("focused") or old.get("count") != new.get("count")

    def _detect_user_change(self, old: dict, new: dict) -> bool:
        return old.get("present") != new.get("present")

    def _detect_env_change(self, old: dict, new: dict) -> bool:
        old_cpu = old.get("cpu_percent", 0)
        new_cpu = new.get("cpu_percent", 0)
        return abs(new_cpu - old_cpu) > 20

    def recent(self, event_type: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        events = self._recent_events if event_type is None else [e for e in self._recent_events if e.event_type == event_type]
        return [e.to_dict() for e in events[-limit:]]
