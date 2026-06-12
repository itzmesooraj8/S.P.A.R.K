"""Tool Executor — Dispatches tool calls safely."""

from __future__ import annotations

import logging
from typing import Any, Callable

from spark.core.events import EventBus

logger = logging.getLogger("spark.orchestration.tools")


class ToolExecutor:
    """Dispatches tool calls to registered handlers."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        self._event_bus = event_bus
        self._tools: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, handler: Callable[..., Any]) -> None:
        self._tools[name] = handler
        logger.debug("Tool registered: %s", name)

    def has(self, name: str) -> bool:
        return name in self._tools

    async def execute(self, name: str, args: dict[str, Any] | None = None) -> dict[str, Any]:
        if name not in self._tools:
            return {"success": False, "error": f"Unknown tool: {name}"}

        if self._event_bus:
            self._event_bus.emit("tool.before_execute", {"tool": name, "args": args})

        try:
            result = self._tools[name](**(args or {}))
            if self._event_bus:
                self._event_bus.emit("tool.after_execute", {"tool": name, "success": True})
            return {"success": True, "result": result}
        except Exception as exc:
            logger.error("Tool %s failed: %s", name, exc)
            if self._event_bus:
                self._event_bus.emit("tool.after_execute", {"tool": name, "success": False, "error": str(exc)})
            return {"success": False, "error": str(exc)}

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())
