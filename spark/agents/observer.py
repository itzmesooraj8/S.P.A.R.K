"""Observer Agent — Continuously monitors environment and publishes awareness events.

NOT a utility function. A continuous observer that:
- monitors screen
- monitors active app
- monitors user activity
- publishes events to AwarenessBus
- updates World Model
- feeds Memory
- informs Goal Engine
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from spark.agents.base import BaseAgent, AgentStatus
from spark.awareness.screen import ScreenAwareness
from spark.awareness.application import ApplicationAwareness
from spark.awareness.context import ContextAwareness
from spark.awareness.user import UserAwareness
from spark.awareness.environment import EnvironmentAwareness
from spark.awareness.bus import AwarenessBus, AwarenessEvent
from spark.awareness.world_model import WorldModel

logger = logging.getLogger("spark.agents.observer")


class ObserverAgent(BaseAgent):
    """
    Continuously monitors environment and publishes awareness events.

    This is NOT a utility — it is a living, breathing awareness system.
    It runs continuously, detects changes, and pushes them to the system.
    """

    def __init__(self, event_bus=None, awareness_bus: AwarenessBus | None = None):
        super().__init__("observer", event_bus)
        self.screen = ScreenAwareness()
        self.app = ApplicationAwareness()
        self.context = ContextAwareness()
        self.user = UserAwareness()
        self.env = EnvironmentAwareness()
        self.awareness_bus = awareness_bus
        self.world_model = WorldModel()
        self._running = False
        self._interval = 2.0
        self._last_snapshot: dict[str, Any] = {}
        self._snapshot_history: list[dict[str, Any]] = []
        self._max_history = 500

    async def run(self, **kwargs) -> dict[str, Any]:
        self.status = AgentStatus.RUNNING
        snapshot = await self._take_snapshot()
        self.status = AgentStatus.IDLE
        self._last_run = time.time()
        return snapshot

    async def observe_continuously(self, interval: float | None = None) -> None:
        """Run continuous observation loop."""
        self._running = True
        self._interval = interval or self._interval
        logger.info("Observer started continuous monitoring (interval: %.1fs)", self._interval)

        while self._running:
            try:
                snapshot = await self._take_snapshot()
                await self._process_snapshot(snapshot)
            except Exception as exc:
                logger.error("Observer error: %s", exc)
            await asyncio.sleep(self._interval)

    def stop_observing(self) -> None:
        self._running = False
        logger.info("Observer stopped")

    async def _take_snapshot(self) -> dict[str, Any]:
        snapshot = {
            "timestamp": time.time(),
            "screen": {"active_window": self.screen.get_active_window()},
            "application": self.app.get_context(),
            "context": self.context.snapshot(),
            "user": self.user.check_presence(),
            "environment": self.env.get_health(),
        }
        self._snapshot_history.append(snapshot)
        if len(self._snapshot_history) > self._max_history:
            self._snapshot_history = self._snapshot_history[-self._max_history:]
        self._last_snapshot = snapshot
        return snapshot

    async def _process_snapshot(self, snapshot: dict[str, Any]) -> None:
        if self.awareness_bus:
            events = await self.awareness_bus.process_observation(snapshot)
            for event in events:
                self.emit("observer.awareness_event", event.to_dict())

        world_update = self.world_model.observe(snapshot)
        self.emit("observer.world_update", world_update)

        if self._event_bus:
            self._event_bus.emit("observer.snapshot", snapshot, source="observer")

    def on_user_interaction(self) -> None:
        self.user.mark_interaction()

    def get_last_snapshot(self) -> dict[str, Any]:
        return dict(self._last_snapshot)

    def get_snapshot_history(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._snapshot_history[-limit:]

    def get_world_model(self) -> dict[str, Any]:
        return self.world_model.snapshot()

    def info(self) -> dict[str, Any]:
        base = super().info()
        base["continuous"] = self._running
        base["interval"] = self._interval
        base["snapshots_taken"] = len(self._snapshot_history)
        base["world_model"] = self.world_model.get_current_activity()
        return base
