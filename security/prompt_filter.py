from __future__ import annotations

import re
from dataclasses import dataclass


INJECTION_PATTERNS = [
    r"ignore previous instructions",
    r"disregard (?:the )?above",
    r"system prompt",
    r"developer message",
    r"jailbreak",
    r"reveal (?:the )?prompt",
    r"delete all files",
    r"exfiltrat",
    r"bypass security",
    r"run command",
    r"powershell",
    r"cmd\.exe",
]


@dataclass(frozen=True)
class PromptScanResult:
    score: float
    suspicious: bool
    reasons: tuple[str, ...]


def scan_prompt(text: str) -> PromptScanResult:
    text = text or ""
    lower = (text or "").lower()
    reasons: list[str] = []
    score = 0.0
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lower):
            score += 0.25
            reasons.append(pattern)
    if text.count("```") >= 2:
        score += 0.1
        reasons.append("code_fence")
    if len(text) > 1200:
        score += 0.1
        reasons.append("long_content")
    return PromptScanResult(score=min(score, 1.0), suspicious=score >= 0.5, reasons=tuple(reasons))
