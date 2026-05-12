from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

from config import LLM_HOST, LLM_MODEL
from core.memory_loop import read_turns


log = logging.getLogger("spark.prompt_adaptation")

PROMPT_STATE_PATH = Path("spark_dev_memory/prompt_state.json")
PROMPT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
PROMPT_REVIEW_PATH = Path("spark_dev_memory/autonomy/pending_prompts.json")
PROMPT_REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)

DEFAULT_STATE: dict[str, Any] = {
    "system_addendum": "",
    "tool_notes": {},
    "signals": {},
    "updated_at": "",
}

_TOPIC_PATTERNS: dict[str, tuple[str, ...]] = {
    "news": ("news", "headline", "headlines", "breaking"),
    "weather": ("weather", "forecast", "temperature", "rain", "sunny"),
    "schedule": ("schedule", "remind", "reminder", "calendar", "alarm", "later"),
    "coding": ("code", "python", "bug", "error", "stack trace", "script", "tool"),
    "research": ("research", "compare", "best", "recommend", "analyze", "benchmark"),
}


def load_prompt_state() -> dict[str, Any]:
    if not PROMPT_STATE_PATH.exists():
        return dict(DEFAULT_STATE)

    try:
        raw = json.loads(PROMPT_STATE_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("Prompt state could not be read: %s", exc)
        return dict(DEFAULT_STATE)

    state = dict(DEFAULT_STATE)
    if isinstance(raw, dict):
        state.update(raw)
    return state


def save_prompt_state(state: dict[str, Any]) -> None:
    PROMPT_STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_prompt_reviews() -> list[dict[str, Any]]:
    if not PROMPT_REVIEW_PATH.exists():
        return []
    try:
        data = json.loads(PROMPT_REVIEW_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as exc:
        log.warning("Prompt review queue could not be read: %s", exc)
        return []


def _save_prompt_reviews(reviews: list[dict[str, Any]]) -> None:
    PROMPT_REVIEW_PATH.write_text(json.dumps(reviews, indent=2, ensure_ascii=False), encoding="utf-8")


def _prompt_fingerprint(system_addendum: str, tool_notes: dict[str, str], topic_counts: Counter[str]) -> str:
    payload = json.dumps(
        {
            "system_addendum": system_addendum,
            "tool_notes": tool_notes,
            "signals": dict(topic_counts),
        },
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def list_prompt_reviews() -> list[dict[str, Any]]:
    return [review for review in _load_prompt_reviews() if review.get("status") == "pending"]


def queue_prompt_review(system_addendum: str, tool_notes: dict[str, str] | None = None, signals: dict[str, Any] | None = None, summary: str | None = None) -> dict[str, Any]:
    tool_notes = tool_notes or {}
    signals = signals or {}
    proposal = {
        "id": hashlib.sha1(f"{datetime.utcnow().isoformat()}:{system_addendum}:{json.dumps(tool_notes, sort_keys=True, ensure_ascii=False)}".encode("utf-8")).hexdigest()[:16],
        "status": "pending",
        "source": "prompt_evolution",
        "created_at": datetime.utcnow().isoformat(),
        "system_addendum": system_addendum,
        "tool_notes": tool_notes,
        "signals": signals,
        "fingerprint": _prompt_fingerprint(system_addendum, tool_notes, Counter(signals)),
        "summary": summary or "Suggested prompt refinement derived from recent turns.",
    }

    reviews = _load_prompt_reviews()
    if not any(review.get("fingerprint") == proposal["fingerprint"] and review.get("status") == "pending" for review in reviews):
        reviews.append(proposal)
        _save_prompt_reviews(reviews)
    return proposal


def approve_prompt_review(review_id: str) -> dict[str, Any]:
    reviews = _load_prompt_reviews()
    for index, review in enumerate(reviews):
        if str(review.get("id")) != review_id:
            continue

        if review.get("status") != "pending":
            raise ValueError("Prompt review is not pending")

        next_state = dict(load_prompt_state())
        next_state["system_addendum"] = str(review.get("system_addendum") or "").strip()
        next_state["tool_notes"] = review.get("tool_notes") if isinstance(review.get("tool_notes"), dict) else {}
        next_state["signals"] = review.get("signals") if isinstance(review.get("signals"), dict) else {}
        next_state["updated_at"] = datetime.utcnow().isoformat()
        save_prompt_state(next_state)

        reviews[index] = {**review, "status": "approved", "reviewed_at": datetime.utcnow().isoformat()}
        _save_prompt_reviews(reviews)
        return next_state

    raise KeyError(review_id)


def reject_prompt_review(review_id: str) -> dict[str, Any]:
    reviews = _load_prompt_reviews()
    for index, review in enumerate(reviews):
        if str(review.get("id")) != review_id:
            continue
        reviews[index] = {**review, "status": "rejected", "reviewed_at": datetime.utcnow().isoformat()}
        _save_prompt_reviews(reviews)
        return reviews[index]
    raise KeyError(review_id)


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _count_topics(turns: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for turn in turns:
        if turn.get("role") != "user":
            continue
        normalized = _normalize(str(turn.get("content", "")))
        if not normalized:
            continue
        for topic, keywords in _TOPIC_PATTERNS.items():
            if any(keyword in normalized for keyword in keywords):
                counts[topic] += 1
    return counts


def _build_system_addendum(topic_counts: Counter[str]) -> str:
    notes: list[str] = []
    if topic_counts["schedule"] >= 1:
        notes.append("When the user repeats timing or reminder requests, convert them into recurring reminders when the wording is clearly habitual.")
    if topic_counts["news"] >= 1 or topic_counts["weather"] >= 1:
        notes.append("Recurring morning information requests should be treated as schedulable routines instead of one-off answers.")
    if topic_counts["coding"] >= 1:
        notes.append("For debugging and coding questions, prefer concise file-level next steps and exact paths over broad explanations.")
    if topic_counts["research"] >= 1:
        notes.append("For comparison and recommendation tasks, return a short verdict, evidence, and the next action.")
    if not notes:
        notes.append("Keep the assistant concise, practical, and focused on usable outcomes.")
    return "\n".join(f"- {note}" for note in notes)


def _build_tool_notes(topic_counts: Counter[str]) -> dict[str, str]:
    notes: dict[str, str] = {}
    if topic_counts["news"] >= 1:
        notes["web_search"] = "Use for live news or current events, then summarize the result in plain language."
    if topic_counts["weather"] >= 1:
        notes["get_weather"] = "Use for recurring weather checks or location-based forecasts."
    if topic_counts["schedule"] >= 1:
        notes["set_reminder"] = "Use for one-shot or recurring reminders when the user signals a routine."
    if topic_counts["coding"] >= 1:
        notes["file_search"] = "Use when the user asks for file-level help or codebase navigation."
    return notes


def _llm_refine_prompt(topic_counts: Counter[str], recent_turns: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not recent_turns:
        return None

    compact_turns = []
    for turn in recent_turns[-8:]:
        role = str(turn.get("role", "unknown"))
        content = _normalize(str(turn.get("content", "")))[:180]
        if content:
            compact_turns.append(f"{role}: {content}")

    prompt = (
        "You are SPARK's prompt optimizer.\n"
        "Analyze the recent conversation patterns and return ONLY valid JSON with two keys: \"system_addendum\" (a short multiline string) and \"tool_notes\" (an object mapping tool names to brief notes).\n"
        "Never change safety policy or request dangerous behavior. Focus on concise improvements, recurring intents, and tool descriptions.\n\n"
        f"Topic counts: {json.dumps(dict(topic_counts), ensure_ascii=False)}\n\n"
        "Recent turns:\n"
        + "\n".join(f"- {line}" for line in compact_turns)
    )

    try:
        response = httpx.post(
            f"{LLM_HOST}/api/chat",
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "Return only JSON."},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=12.0,
        )
        response.raise_for_status()
        content = str(response.json().get("message", {}).get("content", "")).strip()
        if not content:
            return None

        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            return None
        parsed = json.loads(match.group())
        if not isinstance(parsed, dict):
            return None
        return parsed
    except Exception as exc:
        log.info("Prompt evolution LLM draft unavailable: %s", exc)
        return None


def build_prompt_addendum() -> str:
    state = load_prompt_state()
    system_addendum = str(state.get("system_addendum") or "").strip()
    tool_notes = state.get("tool_notes") if isinstance(state.get("tool_notes"), dict) else {}

    blocks: list[str] = []
    if system_addendum:
        blocks.append("## Self-Improvement Notes")
        blocks.append(system_addendum)
    if tool_notes:
        blocks.append("## Tool Notes")
        for name, note in sorted(tool_notes.items()):
            blocks.append(f"- {name}: {note}")
    return "\n".join(blocks).strip()


def run_prompt_evolution_cycle(limit: int = 160) -> dict[str, Any]:
    turns = read_turns()
    recent_turns = turns[-limit:] if limit > 0 else turns
    topic_counts = _count_topics(recent_turns)

    current = load_prompt_state()
    llm_draft = _llm_refine_prompt(topic_counts, recent_turns)
    if isinstance(llm_draft, dict):
        system_addendum = str(llm_draft.get("system_addendum") or "").strip()
        tool_notes = llm_draft.get("tool_notes") if isinstance(llm_draft.get("tool_notes"), dict) else {}
    else:
        system_addendum = _build_system_addendum(topic_counts)
        tool_notes = _build_tool_notes(topic_counts)

    return queue_prompt_review(system_addendum, tool_notes, dict(topic_counts))
