from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Intent:
    name: str
    confidence: float
    route: str
    preferred_inference: str
    requires_confirmation: bool = False
    entities: dict[str, Any] = field(default_factory=dict)
    summary: str = ""


class IntentEngine:
    def resolve(self, text: str, context: dict[str, Any] | None = None) -> Intent:
        raw = (text or "").strip()
        lower = raw.lower()
        context = context or {}

        if any(word in lower for word in ["delete", "remove", "erase", "wipe"]):
            return Intent(
                name="dangerous_action",
                confidence=0.92,
                route="action",
                preferred_inference="local",
                requires_confirmation=True,
                entities={"text": raw},
                summary="Potentially destructive action requires explicit confirmation.",
            )

        if any(word in lower for word in ["open", "launch", "start", "run", "browse"]):
            return Intent(
                name="desktop_action",
                confidence=0.88,
                route="action",
                preferred_inference="local",
                entities={"text": raw, "target": context.get("target")},
                summary="Desktop control or application launch.",
            )

        if any(word in lower for word in ["search", "find", "research", "lookup", "summarize"]):
            return Intent(
                name="research",
                confidence=0.84,
                route="research",
                preferred_inference="hybrid" if context.get("cloud_allowed", True) else "local",
                entities={"query": raw},
                summary="Information retrieval and synthesis.",
            )

        if any(word in lower for word in ["code", "python", "bug", "error", "stack trace"]):
            return Intent(
                name="coding",
                confidence=0.9,
                route="coding",
                preferred_inference="cloud",
                entities={"text": raw},
                summary="Programming or debugging assistance.",
            )

        if any(word in lower for word in ["screen", "window", "tab", "pdf", "visible", "what is on"]):
            return Intent(
                name="vision",
                confidence=0.86,
                route="vision",
                preferred_inference="cloud" if context.get("vision_cloud_ok", True) else "local",
                entities={"text": raw},
                summary="Screen or visual context analysis.",
            )

        if any(word in lower for word in ["remember", "recall", "what did i", "last time", "yesterday"]):
            return Intent(
                name="memory",
                confidence=0.87,
                route="memory",
                preferred_inference="local",
                entities={"text": raw},
                summary="Memory retrieval or conversational recall.",
            )

        if any(word in lower for word in ["remind", "schedule", "calendar", "alarm", "later"]):
            return Intent(
                name="scheduler",
                confidence=0.89,
                route="scheduler",
                preferred_inference="local",
                entities={"text": raw},
                summary="Timed task or reminder request.",
            )

        return Intent(
            name="respond",
            confidence=0.6,
            route="general",
            preferred_inference="local" if context.get("private", True) else "hybrid",
            entities={"text": raw},
            summary="General assistant response.",
        )
