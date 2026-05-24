from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any


@dataclass(frozen=True, slots=True)
class SchemaValidation:
    allowed: bool
    reasons: frozenset[str] = field(default_factory=frozenset)
    cleaned_payload: dict[str, Any] = field(default_factory=dict)
    cleaned_text: str = ""


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def extract_json_object(raw: Any) -> dict[str, Any] | None:
    if isinstance(raw, dict):
        return raw

    if not isinstance(raw, str):
        return None

    text = raw.strip()
    if not text:
        return None

    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()

    if not text.startswith(("{", "[")):
        start_candidates = [index for index in (text.find("{"), text.find("[")) if index != -1]
        if not start_candidates:
            return None
        start = min(start_candidates)
        end = max(text.rfind("}"), text.rfind("]"))
        if end <= start:
            return None
        text = text[start : end + 1]

    try:
        parsed = json.loads(text)
    except Exception:
        return None

    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        parsed = parsed[0]

    return parsed if isinstance(parsed, dict) else None


def extract_text_from_payload(payload: dict[str, Any]) -> str:
    for key in ("text", "message", "query", "content", "command"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    params = payload.get("params")
    if isinstance(params, dict):
        for key in ("text", "message", "query"):
            value = params.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()

    return ""


def validate_command_payload(payload: Any) -> SchemaValidation:
    if not isinstance(payload, dict):
        return SchemaValidation(False, frozenset({"payload_not_object"}))

    text = extract_text_from_payload(payload)
    cleaned_text = _collapse_whitespace(text)
    if cleaned_text and len(cleaned_text) > 2000:
        return SchemaValidation(False, frozenset({"intent_too_long"}), cleaned_payload={}, cleaned_text=cleaned_text)

    cleaned_payload = {
        "module": _collapse_whitespace(str(payload.get("module") or "agent")) or "agent",
        "action": _collapse_whitespace(str(payload.get("action") or "")),
        "text": cleaned_text,
        "context_snapshot": payload.get("context_snapshot") if isinstance(payload.get("context_snapshot"), dict) else {},
        "params": payload.get("params") if isinstance(payload.get("params"), dict) else {},
    }

    return SchemaValidation(True, frozenset(), cleaned_payload=cleaned_payload, cleaned_text=cleaned_text)


def validate_tool_arguments(raw_arguments: str | dict[str, Any] | None, tool_name: str | None = None) -> SchemaValidation:
    if isinstance(raw_arguments, dict):
        return SchemaValidation(True, frozenset(), cleaned_payload=raw_arguments)

    text = _collapse_whitespace(str(raw_arguments or ""))
    if not text:
        return SchemaValidation(True, frozenset(), cleaned_payload={})

    payload = extract_json_object(text)
    if not isinstance(payload, dict):
        return SchemaValidation(False, frozenset({"tool_arguments_malformed"}), cleaned_payload={})

    if tool_name == "get_weather":
        payload.setdefault("location", str(payload.get("location") or payload.get("value") or payload.get("arg") or "current location"))
    elif tool_name == "get_news":
        payload.setdefault("topic", str(payload.get("topic") or payload.get("value") or payload.get("arg") or "current events"))
    elif tool_name == "web_search":
        payload.setdefault("query", str(payload.get("query") or payload.get("value") or payload.get("arg") or text))
    elif tool_name == "open_url" and "url" not in payload:
        payload["url"] = str(payload.get("value") or payload.get("arg") or "")

    return SchemaValidation(True, frozenset(), cleaned_payload=payload)