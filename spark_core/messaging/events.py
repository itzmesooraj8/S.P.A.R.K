from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class IngressSource(str, Enum):
    HUD_WS = "hud_ws"
    TELEGRAM = "telegram"
    WHATSAPP = "whatsapp"
    WEBHOOK = "webhook"
    INTERNAL = "internal"


@dataclass(slots=True)
class IngressEvent:
    content: str
    source: IngressSource
    user_id: str
    conversation_id: str
    transport_session_id: Optional[str] = None
    platform_message_id: Optional[str] = None
    channel: str = "chat"
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at_ms: int = field(default_factory=lambda: int(time.time() * 1000))

    def memory_session_id(self) -> str:
        sid = (self.conversation_id or "").strip()
        if sid:
            return sid[:128]
        fallback = f"user:{self.user_id}".strip()
        return fallback[:128] if fallback else "default"

    def to_orchestrator_payload(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "data": self.content,
            "session_id": self.transport_session_id,
            "memory_session_id": self.memory_session_id(),
            "user_id": self.user_id,
            "source": self.source.value,
            "channel": self.channel,
            "platform_message_id": self.platform_message_id,
            "metadata": self.metadata,
            "ingress_event_id": self.event_id,
            "pre_saved_user": True,
        }
