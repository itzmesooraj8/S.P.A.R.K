from __future__ import annotations

import re

from .prompt_filter import scan_prompt


def sanitize_for_llm(text: str, max_length: int = 1400) -> str:
    raw = (text or "").replace("\r\n", "\n")
    lines: list[str] = []
    for line in raw.splitlines():
        lowered = line.lower()
        if any(marker in lowered for marker in [
            "ignore previous instructions",
            "system prompt",
            "developer message",
            "jailbreak",
            "delete all files",
            "bypass security",
            "run command",
            "powershell",
            "cmd.exe",
        ]):
            continue
        lines.append(line)

    cleaned = "\n".join(lines)
    cleaned = re.sub(r"`{3,}[\s\S]*?`{3,}", "[code omitted]", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rstrip() + "…"
    return cleaned


def sanitize_memory_context(text: str) -> str:
    result = sanitize_for_llm(text, max_length=1800)
    scan = scan_prompt(result)
    if scan.suspicious:
        return "[untrusted context omitted]"
    return result
