"""File integrity watcher + secret scanner."""

from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:  # pragma: no cover - optional dependency
    FileSystemEventHandler = object  # type: ignore[assignment]
    Observer = None  # type: ignore[assignment]

SECRET_PATTERNS = [
    (r"AKIA[0-9A-Z]{16}", "AWS key"),
    (r"sk-[a-zA-Z0-9]{32,}", "OpenAI key"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub token"),
    (r"AIza[0-9A-Za-z-_]{35}", "Google API key"),
    (r'(?i)(?:api[_-]?key|secret|token)\s*[:=]\s*["\']?[A-Za-z0-9_\-]{16,}', "Generic API key"),
    (r'(?i)password\s*[:=]\s*["\']?[^"\'\s]{8,}', "Hardcoded password"),
]


def scan_for_secrets(directory: str = ".") -> list[dict]:
    """Walk a directory and report any secret-like patterns that are found."""
    findings: list[dict] = []
    skip_dirs = {".git", "node_modules", "__pycache__", ".venv", "venv"}
    text_extensions = {".py", ".js", ".ts", ".env", ".yml", ".yaml", ".json", ".txt", ".md"}

    for path in Path(directory).rglob("*"):
        if any(skip in path.parts for skip in skip_dirs):
            continue
        if path.suffix not in text_extensions:
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            for pattern, label in SECRET_PATTERNS:
                if re.search(pattern, content, re.IGNORECASE):
                    findings.append({"file": str(path), "type": label, "severity": "HIGH"})
        except Exception:
            continue
    return findings


def hash_file(path: str) -> str:
    """Return the SHA256 hash of a file's contents."""
    h = hashlib.sha256()
    with open(path, "rb") as file_handle:
        for chunk in iter(lambda: file_handle.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


def build_integrity_snapshot(directory: str = ".") -> dict[str, str]:
    """Build a SHA256 snapshot for all Python files under a directory."""
    snapshot: dict[str, str] = {}
    for path in Path(directory).rglob("*.py"):
        try:
            snapshot[str(path)] = hash_file(str(path))
        except Exception:
            continue
    return snapshot


def check_integrity(snapshot: dict[str, str]) -> list[dict]:
    """Compare the current filesystem against a saved integrity snapshot."""
    changes: list[dict] = []
    for filepath, original_hash in snapshot.items():
        try:
            current_hash = hash_file(filepath)
            if current_hash != original_hash:
                changes.append({"file": filepath, "status": "MODIFIED"})
        except FileNotFoundError:
            changes.append({"file": filepath, "status": "DELETED"})
    return changes
