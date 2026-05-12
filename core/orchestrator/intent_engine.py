from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

import httpx

from config import LLM_HOST, LLM_MODEL


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

        llm_intent = self._resolve_with_llm(raw, context)
        if llm_intent is not None:
            return llm_intent

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

    def _resolve_with_llm(self, raw: str, context: dict[str, Any]) -> Intent | None:
        if not raw:
            return None

        prompt = f"""You are SPARK's intent router.
Classify the user request into exactly one route: action, research, coding, vision, memory, scheduler, or general.
Return ONLY valid JSON with keys: name, confidence, route, preferred_inference, requires_confirmation, summary, entities.

Rules:
- action: desktop/browser actions like open, launch, click, type.
- research: lookups, comparisons, current information, summaries.
- coding: code, bugs, errors, files, implementation requests.
- vision: screen, window, visible, OCR, image analysis.
- memory: recall, remember, what did I say, history.
- scheduler: reminders, recurring tasks, calendars, alarms.
- general: greetings or general conversation.

User request: {raw}
Context: {json.dumps(context, ensure_ascii=False)}

Return JSON only."""

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
                timeout=5.0,
            )
            response.raise_for_status()
            content = str(response.json().get("message", {}).get("content", "")).strip()
            if not content:
                return None

            match = json.loads(content[content.find("{") : content.rfind("}") + 1]) if "{" in content and "}" in content else json.loads(content)
            if not isinstance(match, dict):
                return None

            name = str(match.get("name") or "respond").strip() or "respond"
            route = str(match.get("route") or "general").strip() or "general"
            preferred_inference = str(match.get("preferred_inference") or ("local" if context.get("private", True) else "hybrid")).strip() or "local"
            summary = str(match.get("summary") or "").strip()
            entities = match.get("entities") if isinstance(match.get("entities"), dict) else {"text": raw}
            confidence = match.get("confidence", 0.65)
            try:
                confidence = float(confidence)
            except Exception:
                confidence = 0.65
            requires_confirmation = bool(match.get("requires_confirmation", False))

            return Intent(
                name=name,
                confidence=confidence,
                route=route,
                preferred_inference=preferred_inference,
                requires_confirmation=requires_confirmation,
                entities=entities,
                summary=summary or f"LLM-routed as {route}.",
            )
        except Exception:
            return None
