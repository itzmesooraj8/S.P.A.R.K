"""Action Registry — Central tool registry with authority checks."""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

from spark.authority.validator import ActionValidator
from spark.authority.policy import Permission
from spark.core.events import EventBus

logger = logging.getLogger("spark.actions.registry")

TOOL_PERMISSION_MAP = {
    "take_screenshot": Permission.READ_SCREEN,
    "open_website": Permission.OPEN_BROWSER,
    "open_application": Permission.OPEN_BROWSER,
    "type_text": Permission.MODIFY_SYSTEM,
    "read_clipboard": Permission.ACCESS_FILES,
    "write_clipboard": Permission.ACCESS_FILES,
    "web_search": Permission.NETWORK_ACCESS,
    "send_email": Permission.SEND_EMAIL,
    "system_monitor": Permission.READ_SCREEN,
    "file_search": Permission.ACCESS_FILES,
}


class ActionRegistry:
    """Central registry for all actions with authority validation."""

    def __init__(self, validator: ActionValidator | None = None, event_bus: EventBus | None = None):
        self._validator = validator or ActionValidator()
        self._event_bus = event_bus
        self._actions: dict[str, Callable[..., Any]] = {}

    def register(self, name: str, handler: Callable[..., Any]) -> None:
        self._actions[name] = handler
        logger.debug("Action registered: %s", name)

    async def execute(self, name: str, args: dict[str, Any] | None = None, source: str = "system") -> dict[str, Any]:
        perm = TOOL_PERMISSION_MAP.get(name, Permission.READ_SCREEN)
        validation = self._validator.validate(perm, name, args)

        if not validation.allowed:
            return {"success": False, "error": validation.reason, "blocked": True}

        if validation.needs_confirmation:
            logger.info("Action %s requires confirmation", name)
            return {"success": False, "error": "Requires user confirmation", "needs_confirmation": True}

        if name not in self._actions:
            return {"success": False, "error": f"Unknown action: {name}"}

        try:
            result = self._actions[name](**(args or {}))
            if self._event_bus:
                self._event_bus.emit("action.executed", {"action": name, "success": True})
            return {"success": True, "result": result}
        except Exception as exc:
            logger.error("Action %s failed: %s", name, exc)
            if self._event_bus:
                self._event_bus.emit("action.executed", {"action": name, "success": False, "error": str(exc)})
            return {"success": False, "error": str(exc)}

    def list_actions(self) -> list[str]:
        return list(self._actions.keys())
