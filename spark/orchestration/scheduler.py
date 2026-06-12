"""Task Scheduler — Schedules and manages recurring/deferred tasks."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine

logger = logging.getLogger("spark.orchestration.scheduler")


class ScheduledTask:
    def __init__(self, name: str, action: Callable[..., Coroutine[Any, Any, Any]], interval: float = 0, delay: float = 0):
        self.name = name
        self.action = action
        self.interval = interval
        self.delay = delay
        self.last_run = 0.0
        self.next_run = time.time() + delay
        self.running = False
        self.enabled = True


class TaskScheduler:
    """Schedules recurring and deferred tasks."""

    def __init__(self) -> None:
        self._tasks: dict[str, ScheduledTask] = {}
        self._running = False

    def schedule(self, name: str, action: Callable[..., Coroutine[Any, Any, Any]], interval: float = 60, delay: float = 0) -> None:
        task = ScheduledTask(name=name, action=action, interval=interval, delay=delay)
        self._tasks[name] = task
        logger.info("Scheduled task: %s (interval: %ds)", name, interval)

    def cancel(self, name: str) -> None:
        if name in self._tasks:
            self._tasks[name].enabled = False
            del self._tasks[name]
            logger.info("Cancelled task: %s", name)

    async def run_once(self) -> None:
        now = time.time()
        for task in list(self._tasks.values()):
            if not task.enabled or task.running:
                continue
            if now >= task.next_run:
                task.running = True
                try:
                    await task.action()
                    task.last_run = now
                    if task.interval > 0:
                        task.next_run = now + task.interval
                except Exception as exc:
                    logger.error("Scheduled task %s failed: %s", task.name, exc)
                finally:
                    task.running = False

    async def run_forever(self, check_interval: float = 1.0) -> None:
        self._running = True
        while self._running:
            await self.run_once()
            await asyncio.sleep(check_interval)

    def stop(self) -> None:
        self._running = False

    def list_tasks(self) -> list[dict[str, Any]]:
        return [
            {"name": t.name, "interval": t.interval, "enabled": t.enabled, "last_run": t.last_run}
            for t in self._tasks.values()
        ]
