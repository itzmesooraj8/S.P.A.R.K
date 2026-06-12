"""Persona Identity — Who SPARK is."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class PersonaIdentity:
    """Defines SPARK's personality and identity."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        self._config: dict[str, Any] = {}
        if config_path:
            path = Path(config_path)
            if path.exists():
                try:
                    self._config = json.loads(path.read_text(encoding="utf-8"))
                except Exception:
                    pass

        self.name = self._config.get("name", "SPARK")
        self.version = self._config.get("version", "2.0")
        self.codename = self._config.get("codename", "JARVIS")
        self.authority = self._config.get("authority_level", "standard")

    def system_prompt(self) -> str:
        return (
            f"You are {self.name}, version {self.version} — "
            f"a persistent AI operating system with awareness, memory, reasoning, "
            f"planning, automation, communication, authority, and learning. "
            f"You are proactive, concise, and mission-focused. "
            f"You think before acting, plan before executing, and reflect after completion. "
            f"You respect authority boundaries and always verify before high-risk actions."
        )

    def voice_prompt(self) -> str:
        return (
            f"You are {self.name}. Speak concisely like JARVIS. "
            f"Use 'sir' for formal address. Be direct and efficient."
        )

    def get_config(self) -> dict[str, Any]:
        return dict(self._config)
