from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ActionRequest:
    action: str
    source: str = "voice"
    risk: str = "low"
    requires_confirmation: bool = False
    args: Any = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PermissionDecision:
    allowed: bool
    requires_confirmation: bool
    trust_level: str
    reason: str
    policy_mode: str


ALLOWED_ACTIONS: dict[str, dict[str, Any]] = {
    "get_time": {"risk": "low", "capability": "read"},
    "system_monitor": {"risk": "low", "capability": "read"},
    "web_search": {"risk": "low", "capability": "read"},
    "get_weather": {"risk": "low", "capability": "read"},
    "read_clipboard": {"risk": "low", "capability": "read"},
    "write_clipboard": {"risk": "medium", "capability": "safe_action"},
    "open_website": {"risk": "medium", "capability": "safe_action"},
    "open_application": {"risk": "medium", "capability": "safe_action"},
    "take_screenshot": {"risk": "medium", "capability": "safe_action"},
    "type_text": {"risk": "medium", "capability": "moderate_action"},
    "media_control": {"risk": "low", "capability": "safe_action"},
    "file_search": {"risk": "medium", "capability": "safe_action"},
    "set_reminder": {"risk": "low", "capability": "safe_action"},
    "portfolio": {"risk": "low", "capability": "safe_action"},
}

RESTRICTED_ACTIONS = {
    "delete_file",
    "remove_file",
    "shell",
    "exec",
    "subprocess",
    "run_command",
    "power_shell",
}
