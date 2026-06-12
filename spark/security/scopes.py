"""Permission Scope — Independently controlled permission scopes."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any

logger = logging.getLogger("spark.security.scopes")


class Scope(str, Enum):
    READ_SCREEN = "read_screen"
    CONTROL_BROWSER = "control_browser"
    SEND_EMAIL = "send_email"
    DELETE_FILES = "delete_files"
    EXECUTE_SHELL = "execute_shell"
    ACCESS_NETWORK = "access_network"
    MODIFY_SYSTEM = "modify_system"
    SPEND_MONEY = "spend_money"
    ACCESS_CAMERA = "access_camera"
    ACCESS_MICROPHONE = "access_microphone"
    CONTROL_IOT = "control_iot"
    SEND_MESSAGES = "send_messages"


class PermissionScope:
    """
    Independently controlled permission scopes.

    Each scope can be:
    - granted (always allowed)
    - denied (always blocked)
    - ask (requires user confirmation)
    """

    def __init__(self) -> None:
        self._scopes: dict[str, str] = {scope.value: "ask" for scope in Scope}
        self._granted: set[str] = set()
        self._denied: set[str] = set()

    def grant(self, scope: Scope) -> None:
        self._scopes[scope.value] = "granted"
        self._granted.add(scope.value)
        self._denied.discard(scope.value)
        logger.info("Scope granted: %s", scope.value)

    def deny(self, scope: Scope) -> None:
        self._scopes[scope.value] = "denied"
        self._denied.add(scope.value)
        self._granted.discard(scope.value)
        logger.info("Scope denied: %s", scope.value)

    def ask(self, scope: Scope) -> None:
        self._scopes[scope.value] = "ask"
        self._granted.discard(scope.value)
        self._denied.discard(scope.value)

    def check(self, scope: Scope) -> str:
        return self._scopes.get(scope.value, "ask")

    def is_granted(self, scope: Scope) -> bool:
        return self._scopes.get(scope.value) == "granted"

    def is_denied(self, scope: Scope) -> bool:
        return self._scopes.get(scope.value) == "denied"

    def needs_confirmation(self, scope: Scope) -> bool:
        return self._scopes.get(scope.value) == "ask"

    def get_all(self) -> dict[str, str]:
        return dict(self._scopes)

    def get_granted(self) -> list[str]:
        return list(self._granted)

    def get_denied(self) -> list[str]:
        return list(self._denied)

    def reset(self) -> None:
        self._scopes = {scope.value: "ask" for scope in Scope}
        self._granted.clear()
        self._denied.clear()
