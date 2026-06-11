"""Persona loading and prompt federation for S.P.A.R.K."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from core.config import PERSONA_DIR, SPARK_PERSONA

logger = logging.getLogger("SPARK_PERSONA_MANAGER")


@dataclass(slots=True)
class PersonaDefinition:
    name: str
    voice_tone: list[str]
    response_style: list[str]
    backronym: str
    system_prompt_instructions: list[str]

    def to_prompt_block(self) -> str:
        tone = ", ".join(self.voice_tone)
        style = ", ".join(self.response_style)
        return (
            "## Persona Identity\n"
            f"Name: {self.name}\n"
            f"Backronym: {self.backronym}\n"
            f"Voice tone: {tone}\n"
            f"Response style: {style}\n"
            + ("\n".join(["System prompt instructions:"] + [f"- {item}" for item in self.system_prompt_instructions]) + "\n" if self.system_prompt_instructions else "")
        )


class PersonaManager:
    """Loads persona profiles from the persona/ directory and emits system prompt blocks."""

    def __init__(self, persona_dir: str | Path | None = None, selected_persona: str | None = None) -> None:
        self.persona_dir = Path(persona_dir or PERSONA_DIR).expanduser().resolve()
        self.selected_persona = self._normalize_name(selected_persona or SPARK_PERSONA)
        self.persona_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _normalize_name(name: str) -> str:
        return Path(str(name).strip().lower()).stem or "spark"

    def list_personas(self) -> list[str]:
        if not self.persona_dir.exists():
            return []
        return sorted(path.stem for path in self.persona_dir.glob("*.json") if path.is_file())

    def load_persona(self, name: str | None = None) -> PersonaDefinition:
        persona_name = self._normalize_name(name or self.selected_persona)
        persona_path = self.persona_dir / f"{persona_name}.json"
        if not persona_path.exists():
            logger.warning("Persona '%s' not found; falling back to spark.", persona_name)
            persona_path = self.persona_dir / "spark.json"

        try:
            payload = json.loads(persona_path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.error("Failed to load persona file %s: %s", persona_path, exc)
            payload = {}

        return self._coerce_persona(payload, fallback_name=persona_path.stem)

    def _coerce_persona(self, payload: dict[str, Any], fallback_name: str) -> PersonaDefinition:
        name = str(payload.get("name") or fallback_name or "SPARK").strip()
        voice_tone = payload.get("voice_tone") or []
        response_style = payload.get("response_style") or []
        backronym = str(payload.get("backronym") or "Sentient Proactive Autonomous Response Kernel").strip()
        system_prompt_instructions = payload.get("system_prompt_instructions") or []

        if isinstance(voice_tone, str):
            voice_tone = [item.strip() for item in voice_tone.split(",") if item.strip()]
        if isinstance(response_style, str):
            response_style = [item.strip() for item in response_style.split(",") if item.strip()]
        if isinstance(system_prompt_instructions, str):
            system_prompt_instructions = [item.strip() for item in system_prompt_instructions.split("\n") if item.strip()]

        return PersonaDefinition(
            name=name,
            voice_tone=[str(item).strip() for item in voice_tone if str(item).strip()],
            response_style=[str(item).strip() for item in response_style if str(item).strip()],
            backronym=backronym,
            system_prompt_instructions=[str(item).strip() for item in system_prompt_instructions if str(item).strip()],
        )

    @lru_cache(maxsize=8)
    def get_selected_persona(self) -> PersonaDefinition:
        return self.load_persona(self.selected_persona)

    def build_system_block(self) -> str:
        persona = self.get_selected_persona()
        return persona.to_prompt_block()

    def build_session_metadata(self) -> dict[str, Any]:
        persona = self.get_selected_persona()
        return {
            "active_persona": {
                "name": persona.name,
                "voice_tone": persona.voice_tone,
                "response_style": persona.response_style,
                "backronym": persona.backronym,
            }
        }


def get_persona_manager(selected_persona: str | None = None) -> PersonaManager:
    return PersonaManager(selected_persona=selected_persona)
