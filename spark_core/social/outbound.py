from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

from memory.conversation_memory import ConversationMemory


def _safe_text(value: Any) -> str:
    return str(value or "").strip()


def _extract_prefixed_id(value: str, prefix: str) -> str:
    if value.startswith(prefix):
        return value[len(prefix) :].strip()
    return value.strip()


def _trim_text(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max(1, max_len - 1)] + "..."


async def send_telegram_message(
    *,
    chat_id: str,
    text: str,
    bot_token: str,
    reply_to_message_id: Optional[str] = None,
):
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload: Dict[str, Any] = {
        "chat_id": chat_id,
        "text": _trim_text(text, 4096),
        "disable_web_page_preview": True,
    }
    if reply_to_message_id:
        try:
            payload["reply_to_message_id"] = int(str(reply_to_message_id).strip())
            payload["allow_sending_without_reply"] = True
        except ValueError:
            pass

    timeout = httpx.Timeout(connect=8.0, read=15.0, write=15.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()


async def send_whatsapp_message(
    *,
    to: str,
    text: str,
    access_token: str,
    phone_number_id: str,
    reply_to_message_id: Optional[str] = None,
):
    graph_base = os.getenv("WHATSAPP_GRAPH_API_BASE", "https://graph.facebook.com").rstrip("/")
    api_version = os.getenv("WHATSAPP_GRAPH_API_VERSION", "v21.0").strip() or "v21.0"
    url = f"{graph_base}/{api_version}/{phone_number_id}/messages"

    payload: Dict[str, Any] = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {
            "preview_url": False,
            "body": _trim_text(text, 4096),
        },
    }
    if reply_to_message_id:
        payload["context"] = {"message_id": reply_to_message_id}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    timeout = httpx.Timeout(connect=8.0, read=20.0, write=15.0, pool=5.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()


class SocialOutboundDispatcher:
    def __init__(self):
        self.memory = ConversationMemory()

    async def _resolve_delivery_context(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        context = dict(payload or {})
        metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else {}
        context["metadata"] = metadata

        source = _safe_text(context.get("source")).lower()
        memory_session_id = _safe_text(context.get("memory_session_id"))

        needs_lookup = not source or source in {"", "unknown", "none"}
        if needs_lookup and memory_session_id:
            route = await self.memory.get_last_user_route(memory_session_id)
            if route:
                if not _safe_text(context.get("source")):
                    context["source"] = route.get("source")
                if not _safe_text(context.get("user_id")):
                    context["user_id"] = route.get("user_id")
                if not _safe_text(context.get("channel")):
                    context["channel"] = route.get("channel")
                if not _safe_text(context.get("platform_message_id")):
                    context["platform_message_id"] = route.get("platform_message_id")
                route_metadata = route.get("metadata") if isinstance(route.get("metadata"), dict) else {}
                if route_metadata:
                    merged = {**route_metadata, **context["metadata"]}
                    context["metadata"] = merged

        return context

    async def dispatch(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(payload, dict):
            return {"status": "ignored", "reason": "invalid payload"}

        context = await self._resolve_delivery_context(payload)

        text = _safe_text(context.get("text"))
        if not text:
            return {"status": "ignored", "reason": "empty assistant text"}

        source = _safe_text(context.get("source")).lower()
        if source in {"", "hud_ws", "internal", "webhook"}:
            return {"status": "ignored", "reason": f"source '{source or 'none'}' has no outbound adapter"}

        if source == "telegram":
            return await self._dispatch_telegram(context, text)

        if source == "whatsapp":
            return await self._dispatch_whatsapp(context, text)

        return {"status": "ignored", "reason": f"unsupported source '{source}'"}

    async def _dispatch_telegram(self, context: Dict[str, Any], text: str) -> Dict[str, Any]:
        bot_token = _safe_text(
            os.getenv("TELEGRAM_BOT_TOKEN")
            or os.getenv("SPARK_TELEGRAM_BOT_TOKEN")
        )
        if not bot_token:
            return {"status": "skipped", "reason": "TELEGRAM_BOT_TOKEN not configured"}

        metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else {}
        chat_id = _safe_text(metadata.get("chat_id"))
        if not chat_id:
            memory_session_id = _safe_text(context.get("memory_session_id"))
            if memory_session_id.startswith("telegram:"):
                chat_id = _extract_prefixed_id(memory_session_id, "telegram:")

        if not chat_id:
            user_id = _safe_text(context.get("user_id"))
            chat_id = _extract_prefixed_id(user_id, "telegram:")

        if not chat_id:
            return {"status": "failed", "reason": "telegram chat_id not resolvable"}

        reply_to_message_id = _safe_text(context.get("platform_message_id")) or None

        try:
            result = await send_telegram_message(
                chat_id=chat_id,
                text=text,
                bot_token=bot_token,
                reply_to_message_id=reply_to_message_id,
            )
            return {
                "status": "sent",
                "source": "telegram",
                "chat_id": chat_id,
                "message_id": (result.get("result") or {}).get("message_id"),
            }
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300] if exc.response is not None else ""
            print(f"⚠️ [SocialOutbound] Telegram HTTP error {exc.response.status_code if exc.response else '?'}: {body}")
            return {"status": "failed", "source": "telegram", "error": str(exc)}
        except Exception as exc:
            print(f"⚠️ [SocialOutbound] Telegram dispatch failed: {type(exc).__name__}: {exc}")
            return {"status": "failed", "source": "telegram", "error": str(exc)}

    async def _dispatch_whatsapp(self, context: Dict[str, Any], text: str) -> Dict[str, Any]:
        access_token = _safe_text(
            os.getenv("WHATSAPP_ACCESS_TOKEN")
            or os.getenv("SPARK_WHATSAPP_ACCESS_TOKEN")
        )
        if not access_token:
            return {"status": "skipped", "reason": "WHATSAPP_ACCESS_TOKEN not configured"}

        metadata = context.get("metadata") if isinstance(context.get("metadata"), dict) else {}
        phone_number_id = _safe_text(
            metadata.get("phone_number_id")
            or os.getenv("WHATSAPP_PHONE_NUMBER_ID")
            or os.getenv("SPARK_WHATSAPP_PHONE_NUMBER_ID")
        )
        if not phone_number_id:
            return {"status": "failed", "reason": "whatsapp phone_number_id not configured"}

        recipient = _safe_text(metadata.get("to") or metadata.get("recipient"))
        if not recipient:
            user_id = _safe_text(context.get("user_id"))
            recipient = _extract_prefixed_id(user_id, "whatsapp:")

        if not recipient:
            memory_session_id = _safe_text(context.get("memory_session_id"))
            recipient = _extract_prefixed_id(memory_session_id, "whatsapp:")

        if not recipient:
            return {"status": "failed", "reason": "whatsapp recipient not resolvable"}

        reply_to_message_id = _safe_text(context.get("platform_message_id")) or None

        try:
            result = await send_whatsapp_message(
                to=recipient,
                text=text,
                access_token=access_token,
                phone_number_id=phone_number_id,
                reply_to_message_id=reply_to_message_id,
            )
            return {
                "status": "sent",
                "source": "whatsapp",
                "to": recipient,
                "message_id": ((result.get("messages") or [{}])[0] or {}).get("id"),
            }
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:300] if exc.response is not None else ""
            print(f"⚠️ [SocialOutbound] WhatsApp HTTP error {exc.response.status_code if exc.response else '?'}: {body}")
            return {"status": "failed", "source": "whatsapp", "error": str(exc)}
        except Exception as exc:
            print(f"⚠️ [SocialOutbound] WhatsApp dispatch failed: {type(exc).__name__}: {exc}")
            return {"status": "failed", "source": "whatsapp", "error": str(exc)}


social_dispatcher = SocialOutboundDispatcher()
