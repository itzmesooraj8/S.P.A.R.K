from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Response

from messaging.events import IngressSource
from messaging.ingress import IngressValidationError, ingress_service

webhook_router = APIRouter(prefix="/webhooks", tags=["webhooks"])


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _extract_signature(headers: Any) -> str:
    for key in (
        "x-spark-signature",
        "x-hub-signature-256",
        "x-signature",
        "x-webhook-signature",
    ):
        value = headers.get(key)
        if value:
            return value.strip()
    return ""


def _verify_hmac_signature(raw_body: bytes, signature_header: str, secret: str) -> bool:
    if not signature_header or not secret:
        return False

    provided = signature_header
    if "=" in provided:
        _, provided = provided.split("=", 1)

    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided.lower(), expected.lower())


def _verify_payload(platform: str, request: Request, raw_body: bytes):
    secret = os.getenv("SPARK_WEBHOOK_SECRET", "").strip()
    allow_unsigned = os.getenv("SPARK_ALLOW_UNSIGNED_WEBHOOKS", "false").strip().lower() == "true"

    if not secret and not allow_unsigned:
        raise HTTPException(
            status_code=503,
            detail="Webhook secret not configured. Set SPARK_WEBHOOK_SECRET.",
        )

    if secret:
        signature = _extract_signature(request.headers)
        if not _verify_hmac_signature(raw_body, signature, secret):
            raise HTTPException(status_code=401, detail="Invalid or missing webhook signature.")

    if platform == "telegram":
        expected_header = os.getenv("SPARK_TELEGRAM_SECRET_TOKEN", "").strip()
        if expected_header:
            provided = request.headers.get("x-telegram-bot-api-secret-token", "").strip()
            if not hmac.compare_digest(provided, expected_header):
                raise HTTPException(status_code=401, detail="Invalid Telegram secret token header.")


def _parse_generic(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    content = _as_text(payload.get("message") or payload.get("text") or payload.get("content"))
    if not content:
        return None

    user_id = _as_text(payload.get("user_id") or payload.get("from") or payload.get("sender"))
    if not user_id:
        user_id = "external"

    conversation_id = _as_text(payload.get("conversation_id") or payload.get("session_id"))
    if not conversation_id:
        conversation_id = f"webhook:{user_id}"

    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}

    return {
        "content": content,
        "user_id": user_id,
        "conversation_id": conversation_id,
        "platform_message_id": _as_text(payload.get("message_id") or payload.get("id")) or None,
        "metadata": metadata,
    }


def _parse_telegram(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    message = payload.get("message") or payload.get("edited_message")
    if not isinstance(message, dict):
        return None

    content = _as_text(message.get("text") or message.get("caption"))
    if not content:
        return None

    sender = message.get("from") if isinstance(message.get("from"), dict) else {}
    chat = message.get("chat") if isinstance(message.get("chat"), dict) else {}
    sender_id = _as_text(sender.get("id") or chat.get("id") or "anonymous")
    chat_id = _as_text(chat.get("id") or sender_id)

    return {
        "content": content,
        "user_id": f"telegram:{sender_id}",
        "conversation_id": f"telegram:{chat_id}",
        "platform_message_id": _as_text(message.get("message_id") or payload.get("update_id")) or None,
        "metadata": {
            "update_id": payload.get("update_id"),
            "chat_type": chat.get("type"),
            "username": sender.get("username"),
            "first_name": sender.get("first_name"),
        },
    }


def _extract_whatsapp_text(message: Dict[str, Any]) -> str:
    text_obj = message.get("text") if isinstance(message.get("text"), dict) else {}
    body = _as_text(text_obj.get("body"))
    if body:
        return body

    interactive = message.get("interactive") if isinstance(message.get("interactive"), dict) else {}
    button_reply = interactive.get("button_reply") if isinstance(interactive.get("button_reply"), dict) else {}
    list_reply = interactive.get("list_reply") if isinstance(interactive.get("list_reply"), dict) else {}
    interactive_text = _as_text(button_reply.get("title") or list_reply.get("title"))
    if interactive_text:
        return interactive_text

    image_obj = message.get("image") if isinstance(message.get("image"), dict) else {}
    return _as_text(image_obj.get("caption"))


def _parse_whatsapp(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    entries = payload.get("entry")
    if not isinstance(entries, list):
        return None

    for entry in entries:
        if not isinstance(entry, dict):
            continue
        changes = entry.get("changes")
        if not isinstance(changes, list):
            continue
        for change in changes:
            if not isinstance(change, dict):
                continue
            value = change.get("value") if isinstance(change.get("value"), dict) else {}
            messages = value.get("messages") if isinstance(value.get("messages"), list) else []
            if not messages:
                continue
            message = messages[0] if isinstance(messages[0], dict) else {}

            content = _extract_whatsapp_text(message)
            if not content:
                continue

            sender = _as_text(message.get("from") or "unknown")
            metadata = value.get("metadata") if isinstance(value.get("metadata"), dict) else {}
            phone_number_id = _as_text(metadata.get("phone_number_id") or "")
            conversation_key = sender or phone_number_id or "unknown"

            return {
                "content": content,
                "user_id": f"whatsapp:{sender or 'unknown'}",
                "conversation_id": f"whatsapp:{conversation_key}",
                "platform_message_id": _as_text(message.get("id")) or None,
                "metadata": {
                    "phone_number_id": phone_number_id,
                    "profile_name": ((value.get("contacts") or [{}])[0] or {}).get("profile", {}).get("name"),
                    "message_type": message.get("type"),
                },
            }

    return None


def _parse_payload(platform: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if platform == "telegram":
        return _parse_telegram(payload)
    if platform == "whatsapp":
        return _parse_whatsapp(payload)
    return _parse_generic(payload)


def _source_for(platform: str) -> IngressSource:
    if platform == "telegram":
        return IngressSource.TELEGRAM
    if platform == "whatsapp":
        return IngressSource.WHATSAPP
    return IngressSource.WEBHOOK


async def _handle_social_webhook(platform: str, request: Request) -> Dict[str, Any]:
    normalized_platform = platform.strip().lower()
    if normalized_platform not in {"generic", "telegram", "whatsapp"}:
        raise HTTPException(status_code=404, detail=f"Unsupported platform '{platform}'.")

    raw_body = await request.body()
    _verify_payload(normalized_platform, request, raw_body)

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON webhook payload.") from exc

    parsed = _parse_payload(normalized_platform, payload)
    if not parsed:
        return {
            "status": "ignored",
            "reason": "No text message found in payload.",
        }

    try:
        event = await ingress_service.ingest_text(
            content=parsed["content"],
            source=_source_for(normalized_platform),
            user_id=parsed["user_id"],
            conversation_id=parsed.get("conversation_id"),
            transport_session_id=None,
            platform_message_id=parsed.get("platform_message_id"),
            channel="social",
            metadata={
                "platform": normalized_platform,
                **(parsed.get("metadata") or {}),
            },
        )
    except IngressValidationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc

    return {
        "status": "accepted",
        "event_id": event.event_id,
        "memory_session_id": event.memory_session_id(),
        "source": event.source.value,
    }


@webhook_router.get("/health")
async def webhook_health():
    secret_set = bool(os.getenv("SPARK_WEBHOOK_SECRET", "").strip())
    allow_unsigned = os.getenv("SPARK_ALLOW_UNSIGNED_WEBHOOKS", "false").strip().lower() == "true"
    return {
        "status": "ok",
        "signature_enforced": secret_set and not allow_unsigned,
        "allow_unsigned": allow_unsigned,
    }


@webhook_router.get("/whatsapp")
async def whatsapp_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    verify_token = request.query_params.get("hub.verify_token", "")
    challenge = request.query_params.get("hub.challenge", "")
    expected = os.getenv("SPARK_WHATSAPP_VERIFY_TOKEN", "").strip()

    if mode == "subscribe" and expected and hmac.compare_digest(verify_token, expected):
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="WhatsApp verification failed.")


@webhook_router.post("/social/{platform}")
async def social_webhook(platform: str, request: Request):
    return await _handle_social_webhook(platform, request)


@webhook_router.post("/telegram")
async def telegram_webhook(request: Request):
    return await _handle_social_webhook("telegram", request)


@webhook_router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    return await _handle_social_webhook("whatsapp", request)
