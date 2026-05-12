from __future__ import annotations

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
    next_state = dict(current)
    llm_draft = _llm_refine_prompt(topic_counts, recent_turns)
    if isinstance(llm_draft, dict):
        system_addendum = str(llm_draft.get("system_addendum") or "").strip()
        tool_notes = llm_draft.get("tool_notes") if isinstance(llm_draft.get("tool_notes"), dict) else {}
        next_state["system_addendum"] = system_addendum or _build_system_addendum(topic_counts)
        next_state["tool_notes"] = tool_notes or _build_tool_notes(topic_counts)
    else:
        next_state["system_addendum"] = _build_system_addendum(topic_counts)
        next_state["tool_notes"] = _build_tool_notes(topic_counts)
    next_state["signals"] = dict(topic_counts)
    next_state["updated_at"] = datetime.utcnow().isoformat()

    changed = next_state != current
    if changed:
        save_prompt_state(next_state)
        log.info("Prompt evolution cycle updated the runtime notes.")

    return next_state
