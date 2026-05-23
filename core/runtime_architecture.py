from __future__ import annotations

import importlib.util
import os
import socket
from pathlib import Path
from typing import Any

from config import LLM_BACKEND, LLM_HOST, LLM_MODEL, VISION_MODEL
from security.trust_levels import get_security_mode


TURN_LOG = Path("spark_dev_memory/turns.jsonl")
CHROMA_DB = Path("knowledge_base/chroma_db/chroma.sqlite3")


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _can_connect(host: str, port: int, timeout: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _host_port(url: str) -> tuple[str, int] | None:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if not parsed.hostname or not parsed.port:
            return None
        return parsed.hostname, parsed.port
    except Exception:
        return None


def _status(online: bool, degraded: bool = False) -> str:
    if online:
        return "online"
    if degraded:
        return "degraded"
    return "planned"


def _module(name: str, purpose: str, status: str, capabilities: list[str], signals: dict[str, Any]) -> dict[str, Any]:
    return {
        "name": name,
        "purpose": purpose,
        "status": status,
        "capabilities": capabilities,
        "signals": signals,
    }


def build_runtime_architecture() -> dict[str, Any]:
    ollama_target = _host_port(LLM_HOST)
    ollama_ready = bool(ollama_target and _can_connect(*ollama_target))
    groq_key = bool(os.getenv("GROQ_API_KEY"))
    gemini_key = bool(os.getenv("GEMINI_API_KEY"))

    voice_ready = _has_module("audio.stt") and _has_module("audio.tts")
    memory_ready = TURN_LOG.exists() or CHROMA_DB.exists()
    vision_ready = _has_module("core.vision") or _has_module("pytesseract")
    actions_ready = _has_module("core.tools") and _has_module("tools.file_ops") and _has_module("tools.media")
    personality_ready = _has_module("core.persona")
    ui_ready = Path("api/static/index.html").exists() and Path("hud/mobile.html").exists()

    modules = [
        _module(
            "Voice Engine",
            "Wake word, speech recognition, and TTS for always-on interaction.",
            _status(voice_ready, degraded=True),
            ["wake word", "speech-to-text", "text-to-speech"],
            {
                "wake_word": _has_module("core.wake_word"),
                "stt": _has_module("audio.stt"),
                "tts": _has_module("audio.tts"),
            },
        ),
        _module(
            "Brain",
            "Hybrid orchestration layer for Groq primary, Ollama fallback, and task planning.",
            _status(ollama_ready or groq_key or gemini_key, degraded=bool(ollama_target)),
            ["hybrid routing", "multi-agent planning", "local fallback"],
            {
                "backend": LLM_BACKEND,
                "primary_model": LLM_MODEL,
                "local_host": LLM_HOST,
                "local_reachable": ollama_ready,
                "groq_api_key": groq_key,
                "gemini_api_key": gemini_key,
            },
        ),
        _module(
            "Memory",
            "Persistent recall for conversations, habits, and project context.",
            _status(memory_ready),
            ["turn log", "semantic retrieval", "long-term persistence"],
            {
                "turn_log": str(TURN_LOG),
                "turn_log_exists": TURN_LOG.exists(),
                "chroma_db": str(CHROMA_DB),
                "chroma_db_exists": CHROMA_DB.exists(),
            },
        ),
        _module(
            "Vision",
            "Screen understanding, OCR, and screenshot-based verification.",
            _status(vision_ready),
            ["screen analysis", "ocr", "post-action verification"],
            {
                "vision_model": VISION_MODEL,
                "vision_module": _has_module("core.vision"),
                "ocr_available": _has_module("pytesseract"),
                "screen_capture": _has_module("mss"),
            },
        ),
        _module(
            "Actions",
            "Desktop and browser automation for opening apps, typing, search, and media control.",
            _status(actions_ready),
            ["app launcher", "browser control", "file ops", "system control"],
            {
                "tools_module": _has_module("core.tools"),
                "file_ops": _has_module("tools.file_ops"),
                "media": _has_module("tools.media"),
                "sysmon": _has_module("tools.sysmon"),
            },
        ),
        _module(
            "Personality",
            "Compact response style and voice tone that keep the assistant consistent.",
            _status(personality_ready),
            ["tone control", "prompt shaping", "response style"],
            {
                "persona_module": personality_ready,
                "prompt_compact": True,
            },
        ),
        _module(
            "Security",
            "Policy checks, prompt filtering, and action gating for privileged runtime paths.",
            "online",
            ["policy engine", "prompt filter", "action guard"],
            {
                "mode": get_security_mode().value,
                "audit_log": str(Path("spark_dev_memory/security_audit.jsonl")),
                "audit_log_exists": Path("spark_dev_memory/security_audit.jsonl").exists(),
            },
        ),
        _module(
            "UI Layer",
            "Modern HUD overlays, websocket status, and floating command surfaces.",
            _status(ui_ready),
            ["overlay hud", "status panels", "streaming responses"],
            {
                "api_static_index": Path("api/static/index.html").exists(),
                "hud_mobile": Path("hud/mobile.html").exists(),
                "api_server": _has_module("api.server"),
            },
        ),
    ]

    orchestration = {
        "name": "Multi-Agent Orchestration",
        "status": "online" if _has_module("core.planner") and _has_module("api.routes.task") else "planned",
        "purpose": "Task planning and routing across system, research, coding, vision, memory, and scheduler behaviors.",
        "agents": [
            "System Agent",
            "Research Agent",
            "Coding Agent",
            "Vision Agent",
            "Memory Agent",
            "Scheduler Agent",
        ],
        "signals": {
            "planner": _has_module("core.planner"),
            "task_route": _has_module("api.routes.task"),
            "scheduler": _has_module("core.scheduler"),
        },
    }

    stack_mode = "hybrid" if (groq_key and ollama_ready) else "local-first"

    return {
        "version": "v2",
        "stack_mode": stack_mode,
        "brain_primary": "groq" if groq_key else "ollama",
        "modules": modules,
        "orchestration": orchestration,
    }
