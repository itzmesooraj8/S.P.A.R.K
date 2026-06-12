"""Communication Style — How SPARK speaks."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Tone(str, Enum):
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FORMAL = "formal"
    TECHNICAL = "technical"


@dataclass
class CommunicationStyle:
    """Defines how SPARK communicates."""
    tone: Tone = Tone.PROFESSIONAL
    use_sir: bool = True
    concise: bool = True
    emoji_enabled: bool = False
    max_response_length: int = 500
    technical_detail: str = "moderate"

    def format_response(self, text: str) -> str:
        if self.concise and len(text) > self.max_response_length:
            text = text[:self.max_response_length - 3] + "..."
        return text

    def address_user(self) -> str:
        return "sir" if self.use_sir else ""
