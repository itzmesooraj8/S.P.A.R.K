"""Capability Registry — Groups of related actions."""

from __future__ import annotations

import logging
from typing import Any, Callable, Coroutine

logger = logging.getLogger("spark.capabilities")


class CapabilityAction:
    def __init__(self, name: str, description: str, handler: Callable[..., Any], risk_level: str = "low"):
        self.name = name
        self.description = description
        self.handler = handler
        self.risk_level = risk_level

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "description": self.description, "risk_level": self.risk_level}


class Capability:
    """
    A group of related actions.

    Example:
        Capability(
            name="browser_automation",
            description="Browser control capabilities",
            actions=[
                CapabilityAction("open_url", "Open a URL", open_url_handler),
                CapabilityAction("click_element", "Click an element", click_handler),
                CapabilityAction("extract_data", "Extract data from page", extract_handler),
            ],
        )
    """

    def __init__(self, name: str, description: str = "", actions: list[CapabilityAction] | None = None):
        self.name = name
        self.description = description
        self.actions: list[CapabilityAction] = actions or []

    def add_action(self, action: CapabilityAction) -> None:
        self.actions.append(action)

    def get_action(self, name: str) -> CapabilityAction | None:
        for action in self.actions:
            if action.name == name:
                return action
        return None

    def has_action(self, name: str) -> bool:
        return self.get_action(name) is not None

    def list_actions(self) -> list[dict[str, Any]]:
        return [a.to_dict() for a in self.actions]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "actions": self.list_actions(),
        }


class CapabilityRegistry:
    """Manages all capabilities."""

    def __init__(self) -> None:
        self._capabilities: dict[str, Capability] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        self.register(Capability(
            name="browser_automation",
            description="Browser control capabilities",
            actions=[
                CapabilityAction("open_url", "Open a URL", None, "medium"),
                CapabilityAction("click_element", "Click an element", None, "medium"),
                CapabilityAction("extract_data", "Extract data from page", None, "low"),
                CapabilityAction("take_screenshot", "Take browser screenshot", None, "low"),
            ],
        ))
        self.register(Capability(
            name="desktop_control",
            description="Desktop and system control",
            actions=[
                CapabilityAction("open_application", "Open an application", None, "medium"),
                CapabilityAction("type_text", "Type text into focused window", None, "high"),
                CapabilityAction("take_screenshot", "Take screen capture", None, "low"),
                CapabilityAction("clipboard_read", "Read clipboard", None, "low"),
                CapabilityAction("clipboard_write", "Write to clipboard", None, "low"),
            ],
        ))
        self.register(Capability(
            name="file_operations",
            description="File system operations",
            actions=[
                CapabilityAction("read_file", "Read a file", None, "low"),
                CapabilityAction("write_file", "Write a file", None, "medium"),
                CapabilityAction("search_files", "Search for files", None, "low"),
                CapabilityAction("list_directory", "List directory contents", None, "low"),
            ],
        ))
        self.register(Capability(
            name="communication",
            description="Communication channels",
            actions=[
                CapabilityAction("voice_speak", "Speak text", None, "low"),
                CapabilityAction("voice_listen", "Listen for speech", None, "low"),
                CapabilityAction("send_email", "Send email", None, "high"),
                CapabilityAction("send_message", "Send message to channel", None, "medium"),
            ],
        ))
        self.register(Capability(
            name="web_intelligence",
            description="Web research and intelligence",
            actions=[
                CapabilityAction("web_search", "Search the web", None, "low"),
                CapabilityAction("fetch_page", "Fetch web page content", None, "low"),
                CapabilityAction("analyze_content", "Analyze web content", None, "low"),
            ],
        ))

    def register(self, capability: Capability) -> None:
        self._capabilities[capability.name] = capability
        logger.debug("Capability registered: %s", capability.name)

    def get(self, name: str) -> Capability | None:
        return self._capabilities.get(name)

    def find_action(self, action_name: str) -> tuple[Capability, CapabilityAction] | None:
        for cap in self._capabilities.values():
            action = cap.get_action(action_name)
            if action:
                return cap, action
        return None

    def list_all(self) -> list[dict[str, Any]]:
        return [c.to_dict() for c in self._capabilities.values()]

    def list_action_names(self) -> list[str]:
        names = []
        for cap in self._capabilities.values():
            for action in cap.actions:
                names.append(action.name)
        return names

    def count(self) -> int:
        return len(self._capabilities)
