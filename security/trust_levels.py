from __future__ import annotations

from enum import Enum
import os


class TrustLevel(str, Enum):
    OBSERVER = "observer"
    ASSISTANT = "assistant"
    OPERATOR = "operator"
    DEVELOPER = "developer"
    LOCKED = "locked"


def get_security_mode() -> TrustLevel:
    raw = os.getenv("SPARK_SECURITY_MODE", "assistant").strip().lower()
    try:
        return TrustLevel(raw)
    except Exception:
        return TrustLevel.ASSISTANT


MODE_CAPABILITIES = {
    TrustLevel.OBSERVER: {"read"},
    TrustLevel.ASSISTANT: {"read", "safe_action"},
    TrustLevel.OPERATOR: {"read", "safe_action", "moderate_action"},
    TrustLevel.DEVELOPER: {"read", "safe_action", "moderate_action", "advanced_action"},
    TrustLevel.LOCKED: set(),
}
