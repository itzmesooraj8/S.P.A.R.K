from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal


MoodState = Literal["focused", "stressed", "casual", "curious", "tired"]


@dataclass(frozen=True, slots=True)
class PersonalityProfile:
    mood: MoodState
    verbosity: str
    formality: str
    proactivity: str


MOOD_PROFILES: dict[MoodState, PersonalityProfile] = {
    "focused": PersonalityProfile("focused", "concise", "formal", "low"),
    "stressed": PersonalityProfile("stressed", "concise", "balanced", "low"),
    "casual": PersonalityProfile("casual", "normal", "casual", "medium"),
    "curious": PersonalityProfile("curious", "detailed", "balanced", "high"),
    "tired": PersonalityProfile("tired", "concise", "casual", "low"),
}


TONE_ADDENDA: dict[MoodState, str] = {
    "focused": "User is in deep focus. Be brief and precise. Lead with the answer.",
    "stressed": "User seems stressed. Be calm, clear, and direct. Avoid overwhelming detail.",
    "casual": "User is relaxed. Use a warmer, slightly conversational tone.",
    "curious": "User is exploratory. Add concise context and useful connections.",
    "tired": "User seems tired. Keep responses short and incremental.",
}


class AdaptivePersonality:
    def __init__(self) -> None:
        self.current_mood: MoodState = "casual"
        self._last_update: float = 0.0

    def infer_mood(self, recent_messages: list[str], ambient_context: dict | None = None) -> MoodState:
        combined = " ".join(recent_messages[-5:]).lower()

        # Stress signals
        if any(token in combined for token in ("urgent", "asap", "help", "broken", "error", "fix now", "blocked")):
            return "stressed"

        # Focus signals: terse command-like recent messages
        tail = [msg for msg in recent_messages[-3:] if msg.strip()]
        if tail and all(len(msg.split()) <= 8 for msg in tail):
            return "focused"

        # Curiosity signals
        question_count = combined.count("?")
        if question_count >= 2 or any(token in combined for token in ("why", "how does", "explain", "what if", "compare")):
            return "curious"

        # Tiredness signal from time-of-day
        hour = time.localtime().tm_hour
        if hour >= 23 or hour <= 5:
            return "tired"

        # Ambient context fallback
        context_type = str((ambient_context or {}).get("context_type", "")).lower()
        if context_type == "coding":
            return "focused"

        return "casual"

    def update(self, recent_messages: list[str], ambient_context: dict | None = None) -> None:
        self.current_mood = self.infer_mood(recent_messages, ambient_context=ambient_context)
        self._last_update = time.time()

    def get_tone_addendum(self) -> str:
        profile = MOOD_PROFILES[self.current_mood]
        tone = TONE_ADDENDA[self.current_mood]
        return (
            "\n[ADAPTIVE PERSONALITY] "
            f"Mood={self.current_mood}; Verbosity={profile.verbosity}; "
            f"Formality={profile.formality}; Proactivity={profile.proactivity}; "
            f"Instruction={tone}"
        )

    @property
    def profile(self) -> PersonalityProfile:
        return MOOD_PROFILES[self.current_mood]
