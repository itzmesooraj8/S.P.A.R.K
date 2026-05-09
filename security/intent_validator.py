from __future__ import annotations

from dataclasses import dataclass

from .prompt_filter import scan_prompt


@dataclass(frozen=True)
class IntentValidationResult:
    allowed: bool
    score: float
    reasons: tuple[str, ...]
    cleaned_text: str


def validate_intent_text(text: str) -> IntentValidationResult:
    scan = scan_prompt(text)
    cleaned = text.strip()
    if scan.suspicious and scan.score >= 0.8:
        return IntentValidationResult(False, scan.score, scan.reasons, "")
    return IntentValidationResult(True, scan.score, scan.reasons, cleaned)
