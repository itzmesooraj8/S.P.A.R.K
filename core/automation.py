from __future__ import annotations

import hashlib
import logging
import re
from collections import Counter
from dataclasses import dataclass
from typing import Any

from core.memory_loop import read_turns
from core.scheduler import set_recurring_reminder


logger = logging.getLogger("SPARK_AUTOMATION")


@dataclass(frozen=True)
class ScheduledIntent:
    key: str
    message: str
    hour: int = 8
    minute: int = 0
    day_of_week: str | None = None


RECURRENCE_HINTS = (
    "every day",
    "daily",
    "every morning",
    "every evening",
    "every week",
    "weekly",
    "weekday",
    "weekdays",
    "each morning",
    "each day",
)


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _parse_explicit_time(text: str) -> tuple[int, int] | None:
    match = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    if not match:
        return None

    hour = int(match.group(1))
    minute = int(match.group(2) or 0)
    meridiem = match.group(3)

    if hour == 12:
        hour = 0
    if meridiem == "pm":
        hour += 12

    return hour % 24, minute


def _infer_schedule(text: str) -> ScheduledIntent | None:
    normalized = _normalize(text)
    if not normalized:
        return None

    if not any(hint in normalized for hint in RECURRENCE_HINTS) and "every" not in normalized:
        return None

    if "news" in normalized:
        message = "Morning news briefing"
    elif "weather" in normalized:
        message = "Daily weather briefing"
    elif "brief" in normalized or "briefing" in normalized:
        message = "Daily briefing"
    elif "calendar" in normalized or "schedule" in normalized:
        message = "Schedule check-in"
    else:
        message = text.strip()[:120]

    hour, minute = 8, 0
    if "morning" in normalized:
        hour = 8
    elif "noon" in normalized or "midday" in normalized:
        hour = 12
    elif "evening" in normalized or "night" in normalized:
        hour = 18

    explicit_time = _parse_explicit_time(normalized)
    if explicit_time:
        hour, minute = explicit_time

    day_of_week = "mon-fri" if any(hint in normalized for hint in ("weekday", "weekdays")) else None
    key = hashlib.sha1(f"{message}:{hour}:{minute}:{day_of_week or 'daily'}".encode("utf-8")).hexdigest()[:12]
    return ScheduledIntent(key=key, message=message, hour=hour, minute=minute, day_of_week=day_of_week)


def run_automation_cycle(limit: int = 200) -> list[str]:
    """Scan recent turns and register recurring reminders for repeated scheduling requests."""
    turns = read_turns()
    if not turns:
        return []

    recent_turns = turns[-limit:] if limit > 0 else turns
    user_texts = [str(turn.get("content", "")) for turn in recent_turns if turn.get("role") == "user"]
    if not user_texts:
        return []

    counts: Counter[str] = Counter()
    latest_text_by_key: dict[str, str] = {}
    for text in user_texts:
        intent = _infer_schedule(text)
        if not intent:
            continue
        counts[intent.key] += 1
        latest_text_by_key[intent.key] = text

    scheduled: list[str] = []
    for key, count in counts.items():
        text = latest_text_by_key[key]
        intent = _infer_schedule(text)
        if not intent:
            continue

        should_schedule = count >= 2 or any(hint in _normalize(text) for hint in RECURRENCE_HINTS)
        if not should_schedule:
            continue

        result = set_recurring_reminder(
            intent.message,
            hour=intent.hour,
            minute=intent.minute,
            day_of_week=intent.day_of_week,
        )
        scheduled.append(result)

    if scheduled:
        logger.info("Automation cycle scheduled %d recurring reminder(s).", len(scheduled))
    return scheduled