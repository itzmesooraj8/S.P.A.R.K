# security/intent_validator.py
from typing import NamedTuple, Set

class IntentScan(NamedTuple):
    allowed: bool
    score: float
    reasons: Set[str]
    cleaned_text: str | None = None

def validate_intent_text(text):
    return IntentScan(allowed=True, score=0.0, reasons=set(), cleaned_text=text)
