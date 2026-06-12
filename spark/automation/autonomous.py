"""Autonomous Workflow — Self-executing workflows that run continuously."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine

logger = logging.getLogger("spark.automation.autonomous")


class WorkflowTrigger:
    def __init__(self, name: str, check: Callable[[], Coroutine[Any, Any, bool]], interval: float = 60):
        self.name = name
        self.check = check
        self.interval = interval
        self.last_checked = 0.0


class WorkflowAction:
    def __init__(self, name: str, action: Callable[..., Coroutine[Any, Any, Any]], params: dict[str, Any] | None = None):
        self.name = name
        self.action = action
        self.params = params or {}


class AutonomousWorkflow:
    """
    Self-executing workflows that run continuously.

    Example:
        Monitor email → Detect invoice → Save PDF → Update spreadsheet → Notify user
    """

    def __init__(self) -> None:
        self._workflows: dict[str, dict[str, Any]] = {}
        self._running = False
        self._execution_log: list[dict[str, Any]] = []

    def register(self, name: str, triggers: list[WorkflowTrigger], actions: list[WorkflowAction], description: str = "") -> None:
        self._workflows[name] = {
            "triggers": triggers,
            "actions": actions,
            "description": description,
            "enabled": True,
            "last_run": 0.0,
            "run_count": 0,
        }
        logger.info("Autonomous workflow registered: %s", name)

    async def run_continuous(self, check_interval: float = 10.0) -> None:
        self._running = True
        logger.info("Autonomous workflows started (check interval: %.1fs)", check_interval)

        while self._running:
            for name, workflow in self._workflows.items():
                if not workflow["enabled"]:
                    continue
                for trigger in workflow["triggers"]:
                    if time.time() - trigger.last_checked < trigger.interval:
                        continue
                    trigger.last_checked = time.time()
                    try:
                        if await trigger.check():
                            logger.info("Trigger fired: %s in workflow %s", trigger.name, name)
                            await self._execute_workflow(name)
                    except Exception as exc:
                        logger.error("Trigger check failed: %s in %s", trigger.name, name)
            await asyncio.sleep(check_interval)

    async def _execute_workflow(self, name: str) -> None:
        workflow = self._workflows.get(name)
        if not workflow:
            return

        workflow["last_run"] = time.time()
        workflow["run_count"] += 1

        for action in workflow["actions"]:
            try:
                result = await action.action(**action.params)
                self._execution_log.append({
                    "workflow": name,
                    "action": action.name,
                    "result": str(result)[:200],
                    "success": True,
                    "timestamp": time.time(),
                })
            except Exception as exc:
                self._execution_log.append({
                    "workflow": name,
                    "action": action.name,
                    "error": str(exc),
                    "success": False,
                    "timestamp": time.time(),
                })
                logger.error("Workflow action failed: %s in %s", action.name, name)
                break

    def stop(self) -> None:
        self._running = False

    def enable(self, name: str) -> None:
        if name in self._workflows:
            self._workflows[name]["enabled"] = True

    def disable(self, name: str) -> None:
        if name in self._workflows:
            self._workflows[name]["enabled"] = False

    def list_workflows(self) -> list[dict[str, Any]]:
        return [
            {"name": k, "description": v["description"], "enabled": v["enabled"], "run_count": v["run_count"]}
            for k, v in self._workflows.items()
        ]

    def recent_log(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._execution_log[-limit:]
