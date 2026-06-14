"""Authority Policy — Defines permission levels and rules."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class PermissionLevel(str, Enum):
    DENIED = "denied"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Permission(str, Enum):
    READ_SCREEN = "read_screen"
    OPEN_BROWSER = "open_browser"
    EXECUTE_SHELL = "execute_shell"
    SEND_EMAIL = "send_email"
    SPEND_MONEY = "spend_money"
    ACCESS_FILES = "access_files"
    MODIFY_SYSTEM = "modify_system"
    NETWORK_ACCESS = "network_access"
    VOICE_OUTPUT = "voice_output"
    CAMERA_ACCESS = "camera_access"


@dataclass
class AuthorityPolicy:
    """Defines what actions are allowed at each permission level."""
    level: PermissionLevel = PermissionLevel.MEDIUM
    allowed: list[Permission] = field(default_factory=lambda: [
        Permission.READ_SCREEN,
        Permission.NETWORK_ACCESS,
        Permission.VOICE_OUTPUT,
        Permission.ACCESS_FILES,
        Permission.OPEN_BROWSER,
    ])
    requires_confirmation: list[Permission] = field(default_factory=lambda: [
        Permission.EXECUTE_SHELL,
        Permission.SEND_EMAIL,
    ])
    denied: list[Permission] = field(default_factory=lambda: [
        Permission.SPEND_MONEY,
        Permission.MODIFY_SYSTEM,
    ])

    def is_allowed(self, perm: Permission) -> bool:
        if perm in self.denied:
            return False
        if perm in self.allowed:
            return True
        return perm in self.requires_confirmation

    def needs_confirmation(self, perm: Permission) -> bool:
        return perm in self.requires_confirmation

    def grant(self, perm: Permission) -> None:
        if perm not in self.allowed:
            self.allowed.append(perm)

    def revoke(self, perm: Permission) -> None:
        if perm in self.allowed:
            self.allowed.remove(perm)

    def get_permissions(self) -> dict[str, bool]:
        return {p.value: self.is_allowed(p) for p in Permission}
