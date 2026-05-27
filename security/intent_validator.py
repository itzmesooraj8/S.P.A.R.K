# security/intent_validator.py
from typing import NamedTuple, Set
import re

class IntentScan(NamedTuple):
    allowed: bool
    score: float
    reasons: Set[str]
    cleaned_text: str | None = None


def clean_conversational_filler(text: str) -> str:
    """Strips common leading conversational fillers, greetings, and system words."""
    if not text:
        return ""
    cleaned = text.strip()
    last = None
    # Iteratively strip until string is stable
    while cleaned != last:
        last = cleaned
        # Strip leading whitespace and punctuation
        cleaned = re.sub(r'^[\s.,!?\-;:]+', '', cleaned)
        
        # Leading whitelisted conversational filler words/phrases
        fillers = [
            r"^(?:alright\s+no\s+but\s+listen)\b",
            r"^(?:start\s+creating\s+for\s+me)\b",
            r"^(?:start\s+creating)\b",
            r"^(?:create\s+for\s+me)\b",
            r"^(?:okay\s+so\s+now|hey\s+spark|ok\s+spark|okay\s+spark)\b",
            r"^(?:hey|hi|hello|ok|okay|alright|so|now|yes|no|but|just|please|start|gently|quickly|quietly|look)\b",
            r"^(?:can|could|would|will)\s+you\s+(?:please\s+)?(?:mind\s+)?(?:gently\s+)?(?:just\s+)?",
            r"^(?:hey|hi|hello)\s+spark\b",
            r"^(?:gently|quietly|quickly|please)\b",
        ]
        for pattern in fillers:
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE).strip()
            
    # Strip trailing punctuation/spaces
    cleaned = re.sub(r'[\s.,!?\-;:]+$', '', cleaned)
    return cleaned


def validate_intent_text(text: str) -> IntentScan:
    """Validate intent and return cleaned text."""
    if not text:
        return IntentScan(allowed=True, score=0.0, reasons=set(), cleaned_text="")
        
    cleaned = clean_conversational_filler(text)
    
    # Empty query check after cleaning
    if not cleaned:
        return IntentScan(allowed=True, score=0.0, reasons=set(), cleaned_text="")
        
    if len(cleaned) > 2000:
        return IntentScan(allowed=False, score=1.0, reasons={"intent_too_long"}, cleaned_text=cleaned)
        
    return IntentScan(allowed=True, score=0.0, reasons=set(), cleaned_text=cleaned)
