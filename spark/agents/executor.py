"""Executor Agent — Executes tasks and tool calls."""

from __future__ import annotations

import logging
import time
from typing import Any

from spark.agents.base import BaseAgent, AgentStatus
from spark.orchestration.tool_executor import ToolExecutor

logger = logging.getLogger("spark.agents.executor")


class ExecutorAgent(BaseAgent):
    """Executes planned tasks using available tools."""

    def __init__(self, event_bus=None, tool_executor: ToolExecutor | None = None):
        super().__init__("executor", event_bus)
        self.tool_executor = tool_executor or ToolExecutor(event_bus)

    async def run(self, task: dict[str, Any], **kwargs) -> dict[str, Any]:
        self.status = AgentStatus.RUNNING
        tool_name = task.get("tool_needed", "")
        args = task.get("args", {})
        self.emit("executor.start", {"task": task})

        try:
            if tool_name and self.tool_executor.has(tool_name):
                result = await self.tool_executor.execute(tool_name, args)
            else:
                result = await self._execute_direct(task)

            self.status = AgentStatus.IDLE
            self._last_run = time.time()
            self.emit("executor.done", {"task": task, "result": result})
            return result
        except Exception as exc:
            self.status = AgentStatus.ERROR
            self.emit("executor.error", {"task": task, "error": str(exc)})
            return {"success": False, "error": str(exc)}

    async def _execute_direct(self, task: dict[str, Any]) -> dict[str, Any]:
        return {"success": True, "result": f"Executed: {task.get('description', 'unknown')}"}

    def register_tool(self, name: str, handler) -> None:
        self.tool_executor.register(name, handler)

    def available_tools(self) -> list[str]:
        return self.tool_executor.list_tools()
