"""Action Validator — Validates actions against authority policy."""

from __future__ import annotations

import logging
import time
from typing import Any

from spark.authority.policy import AuthorityPolicy, Permission, PermissionLevel
from spark.core.events import EventBus

logger = logging.getLogger("spark.authority.validator")


class ValidationResult:
    def __init__(self, allowed: bool, reason: str = "", needs_confirmation: bool = False):
        self.allowed = allowed
        self.reason = reason
        self.needs_confirmation = needs_confirmation

    def __bool__(self) -> bool:
        return self.allowed


class ActionValidator:
    """Validates every action against the authority policy."""

    def __init__(self, policy: AuthorityPolicy | None = None, event_bus: EventBus | None = None):
        self.policy = policy or AuthorityPolicy()
        self._event_bus = event_bus
        self._log: list[dict[str, Any]] = []

    def validate(self, permission: Permission, action_name: str = "", args: dict[str, Any] | None = None) -> ValidationResult:
        if permission in self.policy.denied:
            self._log_event(action_name, False, f"Denied: {permission.value}")
            return ValidationResult(allowed=False, reason=f"Permission denied: {permission.value}")

        if permission in self.policy.allowed:
            self._log_event(action_name, True, "Allowed")
            return ValidationResult(allowed=True)

        if permission in self.policy.requires_confirmation:
            self._log_event(action_name, True, f"Requires confirmation: {permission.value}")
            return ValidationResult(allowed=True, needs_confirmation=True, reason="Requires user confirmation")

        self._log_event(action_name, False, f"Unknown permission: {permission.value}")
        return ValidationResult(allowed=False, reason=f"Unknown permission: {permission.value}")

    def validate_tool(self, tool_name: str, source: str = "system") -> ValidationResult:
        tool_permissions = {
            "take_screenshot": Permission.READ_SCREEN,
            "open_website": Permission.OPEN_BROWSER,
            "open_application": Permission.OPEN_BROWSER,
            "type_text": Permission.MODIFY_SYSTEM,
            "read_clipboard": Permission.ACCESS_FILES,
            "write_clipboard": Permission.ACCESS_FILES,
            "web_search": Permission.NETWORK_ACCESS,
            "send_email": Permission.SEND_EMAIL,
            "system_monitor": Permission.READ_SCREEN,
        }
        perm = tool_permissions.get(tool_name, Permission.READ_SCREEN)
        return self.validate(perm, tool_name)

    def _log_event(self, action: str, allowed: bool, reason: str) -> None:
        entry = {"action": action, "allowed": allowed, "reason": reason, "ts": time.time()}
        self._log.append(entry)
        if len(self._log) > 500:
            self._log = self._log[-500:]
        if self._event_bus:
            self._event_bus.emit("authority.check", entry)

    def recent_log(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._log[-limit:]

    def set_level(self, level: PermissionLevel) -> None:
        self.policy.level = level
