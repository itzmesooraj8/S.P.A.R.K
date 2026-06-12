"""Workflow Engine — Executes multi-step workflows."""

from __future__ import annotations

import logging
import time
from typing import Any, Callable, Coroutine

from spark.core.events import EventBus, Event

logger = logging.getLogger("spark.orchestration.workflow")


class WorkflowStep:
    def __init__(self, name: str, action: Callable[..., Coroutine[Any, Any, Any]], params: dict[str, Any] | None = None):
        self.name = name
        self.action = action
        self.params = params or {}
        self.status = "pending"
        self.result = None
        self.started_at = 0.0
        self.completed_at = 0.0


class Workflow:
    def __init__(self, name: str, steps: list[WorkflowStep]):
        self.name = name
        self.steps = steps
        self.current = 0
        self.status = "pending"

    @property
    def is_complete(self) -> bool:
        return self.current >= len(self.steps)


class WorkflowEngine:
    """Orchestrates multi-step workflows."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus
        self._workflows: list[Workflow] = []
        self._completed: list[Workflow] = []

    async def execute(self, workflow: Workflow) -> dict[str, Any]:
        workflow.status = "running"
        self._workflows.append(workflow)
        logger.info("Workflow started: %s (%d steps)", workflow.name, len(workflow.steps))

        while not workflow.is_complete:
            step = workflow.steps[workflow.current]
            step.status = "running"
            step.started_at = time.time()
            try:
                step.result = await step.action(**step.params)
                step.status = "done"
                step.completed_at = time.time()
                if self._event_bus:
                    self._event_bus.emit("workflow.step_done", {"workflow": workflow.name, "step": step.name})
            except Exception as exc:
                step.status = "failed"
                step.result = str(exc)
                logger.error("Step failed: %s in %s", step.name, workflow.name)
                break
            workflow.current += 1

        workflow.status = "completed" if workflow.is_complete else "failed"
        self._workflows.remove(workflow)
        self._completed.append(workflow)
        return {"workflow": workflow.name, "status": workflow.status, "steps_completed": workflow.current}

    def pending(self) -> list[dict[str, Any]]:
        return [{"name": w.name, "steps": len(w.steps), "current": w.current} for w in self._workflows]
