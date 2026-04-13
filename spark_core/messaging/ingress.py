from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional

from memory.conversation_memory import ConversationMemory
from messaging.events import IngressEvent, IngressSource
from system.event_bus import event_bus


class IngressValidationError(ValueError):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


class IngressService:
    def __init__(self):
        self.memory = ConversationMemory()
        self.max_input_chars = max(64, int(os.getenv("SPARK_MAX_INPUT_CHARS", "8000")))
        self.max_metadata_bytes = max(256, int(os.getenv("SPARK_MAX_INGRESS_METADATA_BYTES", "4096")))

    @staticmethod
    def _normalize_id(value: Optional[str], fallback: str, max_len: int = 128) -> str:
        text = str(value or "").strip()
        if text:
            return text[:max_len]
        return fallback[:max_len]

    def _normalize_metadata(self, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not isinstance(metadata, dict):
            return {}

        packed = json.dumps(metadata, ensure_ascii=True, default=str)
        size_bytes = len(packed.encode("utf-8"))
        if size_bytes <= self.max_metadata_bytes:
            return metadata

        return {
            "note": "metadata_truncated",
            "size_bytes": size_bytes,
        }

    async def ingest_text(
        self,
        *,
        content: str,
        source: IngressSource,
        user_id: Optional[str],
        conversation_id: Optional[str] = None,
        transport_session_id: Optional[str] = None,
        platform_message_id: Optional[str] = None,
        channel: str = "chat",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> IngressEvent:
        message = str(content or "").strip()
        if not message:
            raise IngressValidationError("Message is empty.", status_code=400)
        if len(message) > self.max_input_chars:
            raise IngressValidationError(
                f"Message exceeds max length ({self.max_input_chars} chars).",
                status_code=413,
            )

        normalized_user = self._normalize_id(user_id, "anonymous")
        normalized_conversation = self._normalize_id(
            conversation_id,
            f"{source.value}:{normalized_user}",
        )
        normalized_channel = self._normalize_id(channel, "chat", max_len=32)
        normalized_metadata = self._normalize_metadata(metadata)

        event = IngressEvent(
            content=message,
            source=source,
            user_id=normalized_user,
            conversation_id=normalized_conversation,
            transport_session_id=self._normalize_id(
                transport_session_id,
                "",
            )
            or None,
            platform_message_id=self._normalize_id(
                platform_message_id,
                "",
            )
            or None,
            channel=normalized_channel,
            metadata=normalized_metadata,
        )

        await self.memory.save_message(
            event.memory_session_id(),
            "user",
            event.content,
            user_id=event.user_id,
            source=event.source.value,
            channel=event.channel,
            transport_session_id=event.transport_session_id,
            platform_message_id=event.platform_message_id,
            metadata=event.metadata,
        )

        event_bus.publish("ingress_event", event.to_orchestrator_payload())
        return event


ingress_service = IngressService()
