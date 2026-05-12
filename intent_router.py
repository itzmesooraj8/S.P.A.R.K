from __future__ import annotations

import json
import logging
import os
import re
import threading
from dataclasses import asdict, dataclass, field
from typing import Any


logger = logging.getLogger(__name__)

try:
    from config import LLM_HOST, LLM_MODEL
except Exception:
    LLM_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    LLM_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


@dataclass(slots=True)
class Task:
    action: str
    target: str = ""
    params: dict[str, Any] = field(default_factory=dict)


class IntentRouterError(RuntimeError):
    pass


_LOCAL_MODEL: Any | None = None
_LOCAL_MODEL_LOCK = threading.Lock()


def parse_intents(user_input: str) -> list[Task]:
    """Parse one user sentence into one or more executable tasks."""
    text = (user_input or "").strip()
    if not text:
        return []

    groq_tasks = _parse_with_groq(text)
    if groq_tasks:
        return groq_tasks

    local_tasks = _parse_with_local_hf(text)
    if local_tasks:
        return local_tasks

    return _parse_with_regex(text)


def _task_from_payload(payload: dict[str, Any]) -> Task | None:
    action = str(payload.get("action") or "").strip()
    if not action:
        return None
    target = str(payload.get("target") or "").strip()
    params = payload.get("params") if isinstance(payload.get("params"), dict) else {}
    return Task(action=action, target=target, params=dict(params))


def _normalize_tasks(raw: Any) -> list[Task]:
    items: list[Any]
    if isinstance(raw, dict):
        items = raw.get("tasks") or raw.get("intents") or raw.get("items") or []
    elif isinstance(raw, list):
        items = raw
    else:
        return []

    tasks: list[Task] = []
    for item in items:
        if isinstance(item, dict):
            task = _task_from_payload(item)
            if task is not None:
                tasks.append(task)
    return tasks


def _extract_json_text(content: str) -> str:
    stripped = (content or "").strip()
    if not stripped:
        raise IntentRouterError("Empty model response")

    fenced = re.search(r"```(?:json)?\s*(.*?)```", stripped, flags=re.IGNORECASE | re.DOTALL)
    if fenced:
        stripped = fenced.group(1).strip()

    start_candidates = [index for index in (stripped.find("{"), stripped.find("[")) if index != -1]
    if not start_candidates:
        raise IntentRouterError("No JSON payload found")

    start = min(start_candidates)
    end = max(stripped.rfind("}"), stripped.rfind("]"))
    if end < start:
        raise IntentRouterError("Malformed JSON payload")
    return stripped[start : end + 1]


def _parse_json_payload(content: str) -> list[Task]:
    payload = json.loads(_extract_json_text(content))
    return _normalize_tasks(payload)


def _build_groq_prompt(text: str) -> list[dict[str, str]]:
    system_prompt = (
        "You are SPARK's intent router. Extract every distinct user intent from the input. "
        "Return JSON only with this schema: {\"tasks\":[{\"action\":\"...\",\"target\":\"...\",\"params\":{...}}]}. "
        "Do not add commentary. Preserve the order of the user's requests. "
        "Use one task per intent, even when the sentence contains multiple actions."
    )
    user_prompt = f"User input: {text}"
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _get_groq_client():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    try:
        from groq import Groq
    except Exception as exc:
        logger.debug("Groq client unavailable: %s", exc)
        return None

    return Groq(api_key=api_key)


def _call_groq_structured(text: str) -> str:
    client = _get_groq_client()
    if client is None:
        raise IntentRouterError("Groq is unavailable")

    response = client.chat.completions.create(
        model=os.getenv("GROQ_MODEL", LLM_MODEL),
        messages=_build_groq_prompt(text),
        temperature=0,
        stream=False,
    )
    choice = response.choices[0]
    content = getattr(choice.message, "content", None) or ""
    if not content:
        raise IntentRouterError("Groq returned an empty response")
    return str(content)


def _parse_with_groq(text: str) -> list[Task]:
    try:
        return _parse_json_payload(_call_groq_structured(text))
    except Exception as exc:
        logger.debug("Groq intent routing failed: %s", exc)
        return []


def _load_local_model():
    model_id = os.getenv("SPARK_INTENT_LOCAL_MODEL", "").strip()
    if not model_id:
        return None

    try:
        from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
    except Exception as exc:
        logger.debug("Local HuggingFace stack unavailable: %s", exc)
        return None

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = AutoModelForCausalLM.from_pretrained(model_id)
        return pipeline("text-generation", model=model, tokenizer=tokenizer)
    except Exception as exc:
        logger.debug("Local HuggingFace model load failed: %s", exc)
        return None


def _get_local_model():
    global _LOCAL_MODEL
    if _LOCAL_MODEL is not None:
        return _LOCAL_MODEL

    with _LOCAL_MODEL_LOCK:
        if _LOCAL_MODEL is None:
            _LOCAL_MODEL = _load_local_model()
    return _LOCAL_MODEL


def _local_model_prompt(text: str) -> str:
    return (
        "Extract every intent from the user input and return JSON only in the format "
        '{"tasks":[{"action":"...","target":"...","params":{}}]}. '
        f"User input: {text}"
    )


def _parse_with_local_hf(text: str) -> list[Task]:
    model = _get_local_model()
    if model is None:
        return []

    try:
        output = model(_local_model_prompt(text), max_new_tokens=256, do_sample=False)
        if isinstance(output, list) and output:
            first = output[0]
            if isinstance(first, dict):
                generated = str(first.get("generated_text") or first.get("text") or "")
            else:
                generated = str(first)
        else:
            generated = str(output)
        return _parse_json_payload(generated)
    except Exception as exc:
        logger.debug("Local HuggingFace routing failed: %s", exc)
        return []


def _parse_with_regex(text: str) -> list[Task]:
    lower = text.lower()
    tasks: list[Task] = []

    browser_stopwords = {"another", "new", "current", "browser", "tab", "window", "page", "one"}

    def _browser_token(value: str) -> str:
        match = re.search(r"\bin\s+([a-z0-9_.-]+)\b", value, flags=re.IGNORECASE)
        if not match:
            return ""
        token = match.group(1).strip().lower()
        return token if token and token not in browser_stopwords else ""

    def _verb_chunks(value: str) -> list[tuple[str, str]]:
        matches = list(re.finditer(r"\b(?:open|launch|start|run|search|find|look up|lookup|research|weather|forecast|temperature|time|date|clock)\b", value, flags=re.IGNORECASE))
        if not matches:
            return []

        chunks: list[tuple[str, str]] = []
        for index, match in enumerate(matches):
            verb = match.group(0).lower()
            start = match.start()
            end = matches[index + 1].start() if index + 1 < len(matches) else len(value)
            chunks.append((verb, value[start:end]))
        return chunks

    normalized = re.sub(
        r"\bin\s+([a-z0-9_.-]+)\s+(?=(open|launch|start|run|search|find|look up|lookup|research)\b)",
        lambda match: f"[browser={match.group(1).lower()}] ",
        text,
        flags=re.IGNORECASE,
    )

    chunks = _verb_chunks(normalized)
    pending_browser = ""

    for verb, chunk in chunks:
        chunk_lower = chunk.lower()
        chunk_browser = ""

        marker = re.search(r"\[browser=([a-z0-9_.-]+)\]", chunk_lower, flags=re.IGNORECASE)
        if marker:
            candidate = marker.group(1).strip().lower()
            if candidate not in browser_stopwords:
                chunk_browser = candidate
            chunk = re.sub(r"\[browser=[a-z0-9_.-]+\]", " ", chunk, flags=re.IGNORECASE)
            chunk_lower = chunk.lower()

        browser = chunk_browser or pending_browser or _browser_token(chunk)
        if browser:
            pending_browser = browser
        else:
            pending_browser = ""

        if verb in {"open", "launch", "start", "run"}:
            body = re.sub(rf"^\s*{re.escape(verb)}\b", "", chunk, flags=re.IGNORECASE).strip()
            body = re.sub(r"\bin\s+[a-z0-9_.-]+\b", " ", body, flags=re.IGNORECASE).strip()
            if not body:
                continue

            if re.search(r"\b(map|maps|google maps)\b", body, flags=re.IGNORECASE):
                location = re.sub(r"\b(?:open|launch|start|run|map|maps|google|chrome|browser)\b", " ", body, flags=re.IGNORECASE)
                location = re.sub(r"\b(?:and|tab|another|new|current)\b", " ", location, flags=re.IGNORECASE)
                location = _clean_target(location)
                if location:
                    params: dict[str, Any] = {}
                    if browser:
                        params["browser"] = browser
                    tasks.append(Task(action="open_url_in_browser", target=location, params=params))
                pending_browser = ""
                continue

            parts = [part.strip() for part in re.split(r"\b(?:and|,|&|plus|also)\b", body, flags=re.IGNORECASE) if part.strip()]
            if len(parts) > 1:
                for part in parts:
                    cleaned = _clean_target(part)
                    if cleaned:
                        tasks.append(Task(action="open_app", target=cleaned, params={}))
            else:
                cleaned = _clean_target(body)
                if cleaned:
                    tasks.append(Task(action="open_app", target=cleaned, params={}))
            pending_browser = ""
            continue

        if any(word in chunk_lower for word in ["search", "find", "look up", "lookup", "research"]):
            query = re.sub(r"^\s*(?:search|find|look up|lookup|research)\b", "", chunk, flags=re.IGNORECASE).strip()
            query = re.sub(r"\bin\s+[a-z0-9_.-]+\b", " ", query, flags=re.IGNORECASE).strip()
            query = _clean_target(query)
            if not query:
                continue

            params: dict[str, Any] = {}
            if browser:
                params["browser"] = browser
                tasks.append(Task(action="open_url_in_browser", target=query, params=params))
            else:
                tasks.append(Task(action="web_search", target=query, params=params))
            pending_browser = ""
            continue

        if any(word in chunk_lower for word in ["weather", "forecast", "temperature", "rain", "humidity"]):
            location_match = re.search(r"\b(?:in|for|at)\s+(.+)$", chunk, flags=re.IGNORECASE)
            location = location_match.group(1).strip() if location_match else chunk
            location = re.split(r"\b(?:and then|then|and|also|plus)\b|,", location, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            location = _clean_target(location)
            tasks.append(Task(action="get_weather", target=location, params={}))
            pending_browser = ""
            continue

        if any(word in chunk_lower for word in ["time", "date", "clock"]):
            tasks.append(Task(action="get_time", target="", params={}))
            pending_browser = ""
            continue

    if tasks:
        return tasks

    # Fallback single-intent guess from the full text.
    if any(word in lower for word in ["open", "launch", "start", "run"]):
        return [Task(action="open_app", target=_clean_target(text), params={})]
    if any(word in lower for word in ["search", "find", "look up", "lookup", "research"]):
        return [Task(action="web_search", target=text.strip(), params={})]
    if any(word in lower for word in ["weather", "forecast", "temperature", "rain", "humidity"]):
        return [Task(action="get_weather", target=text.strip(), params={})]
    if any(word in lower for word in ["time", "date", "clock"]):
        return [Task(action="get_time", target="", params={})]

    return [Task(action="respond", target=text.strip(), params={})]


def _clean_target(text: str) -> str:
    cleaned = re.sub(
        r"\b(?:please|now|for me|for us|in another tab|in a new tab|new tab|another tab|in chrome|in browser|on chrome|on browser)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    return " ".join(cleaned.split()).strip(" .")


__all__ = ["Task", "IntentRouterError", "parse_intents"]