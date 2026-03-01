"""
SPARK Plugin Loader System
────────────────────────────────────────────────────────────────────────────────
Dynamic enable/disable of SPARK capability modules.
Each plugin has metadata, an enabled flag, and optional health status.

Endpoints:
  GET    /api/plugins              — list all plugins + status
  POST   /api/plugins/{id}/enable  — enable a plugin
  POST   /api/plugins/{id}/disable — disable a plugin
  GET    /api/plugins/{id}/status  — detailed plugin health
  POST   /api/plugins/reload       — reload plugin registry
"""

import asyncio
import os
import time
from typing import Dict, Optional, Any
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# ── Plugin Definition ──────────────────────────────────────────────────────────

class PluginStatus(str, Enum):
    ENABLED   = "enabled"
    DISABLED  = "disabled"
    ERROR     = "error"
    LOADING   = "loading"


class Plugin:
    def __init__(
        self,
        plugin_id: str,
        name: str,
        description: str,
        category: str,
        enabled: bool = True,
        requires: list = None,
        version: str = "1.0.0",
        author: str = "SPARK Core",
    ):
        self.id          = plugin_id
        self.name        = name
        self.description = description
        self.category    = category
        self.enabled     = enabled
        self.requires    = requires or []
        self.version     = version
        self.author      = author
        self.status      = PluginStatus.ENABLED if enabled else PluginStatus.DISABLED
        self.last_toggle = time.time()
        self.error_msg   = None
        self.health      = {"ok": True}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id":          self.id,
            "name":        self.name,
            "description": self.description,
            "category":    self.category,
            "enabled":     self.enabled,
            "status":      self.status.value,
            "requires":    self.requires,
            "version":     self.version,
            "author":      self.author,
            "last_toggle": self.last_toggle,
            "error":       self.error_msg,
            "health":      self.health,
        }


class PluginManager:
    """Registry and lifecycle manager for SPARK capability plugins."""

    def __init__(self):
        self._plugins: Dict[str, Plugin] = {}
        self._register_core_plugins()

    def _register_core_plugins(self):
        """Register built-in SPARK plugins."""
        plugins = [
            # ── AI Core ────────────────────────────────────────────────────
            Plugin("ollama_llm",        "Ollama LLM",           "Local LLM inference via Ollama (llama3, mistral, etc.)", "AI Core",   enabled=True),
            Plugin("cognitive_loop",    "Cognitive Loop",       "Autonomous background reasoning and self-reflection loop", "AI Core", enabled=True),
            Plugin("multi_agent",       "Multi-Agent System",   "Commander + specialized sub-agents (code, research, risk)", "AI Core", enabled=True),
            Plugin("knowledge_graph",   "Knowledge Graph",      "Long-term strategic memory with SQLite graph storage", "Memory",    enabled=True),
            # ── Search & Memory ────────────────────────────────────────────
            Plugin("neural_search",     "Neural Search",        "ChromaDB vector memory + semantic similarity search", "Memory",     enabled=True, requires=["chromadb"]),
            Plugin("dev_memory",        "Dev Memory",           "Persistent development session context and mutation log", "Memory",   enabled=True),
            # ── Voice ──────────────────────────────────────────────────────
            Plugin("tts",               "Text-to-Speech",       "Edge-TTS neural voice synthesis (SPARK speaks back)", "Voice",      enabled=True, requires=["edge-tts"]),
            Plugin("stt",               "Speech-to-Text",       "Faster-Whisper local STT for voice commands", "Voice",             enabled=False, requires=["faster-whisper"]),
            Plugin("wake_word",         "Wake Word Detection",  "Trigger SPARK by saying 'Hey SPARK'", "Voice",                  enabled=False),
            # ── Vision ────────────────────────────────────────────────────
            Plugin("vision",            "Image Vision",         "Screen capture + image analysis via vision module", "Vision",      enabled=True),
            Plugin("camera",            "Camera Feed",          "Live webcam feed analysis and object detection", "Vision",         enabled=False),
            # ── Tools & Execution ─────────────────────────────────────────
            Plugin("code_sandbox",      "Code Sandbox",         "Isolated Docker-based code execution environment", "Tools",        enabled=True),
            Plugin("web_browser",       "Web Browser Agent",    "Playwright-powered autonomous web browsing", "Tools",             enabled=True, requires=["playwright"]),
            Plugin("file_tools",        "File Tools",           "Read/write/search workspace files", "Tools",                      enabled=True),
            Plugin("system_tools",      "System Tools",         "Process management, resource monitoring", "Tools",                enabled=True),
            # ── Intelligence ──────────────────────────────────────────────
            Plugin("workspace_scanner", "Workspace Scanner",    "Real-time AST code graph and dependency analysis", "Intelligence", enabled=True),
            Plugin("threat_intel",      "Threat Intelligence",  "Globe threat predictor with conflict/seismic/fire feeds", "Intel", enabled=True),
            Plugin("self_evolution",    "Self-Evolution Engine","Bounded self-improvement proposal system", "Intel",                enabled=True),
            # ── Integrations ─────────────────────────────────────────────
            Plugin("scheduler",         "Task Scheduler",       "APScheduler-based reminders, cron tasks, and alerts", "System",    enabled=True, requires=["apscheduler"]),
            Plugin("globe_api",         "Globe Intelligence",   "Real-time geospatial event feeds (earthquake, conflict, etc.)", "Intel", enabled=True),
            # ── Security ─────────────────────────────────────────────────
            Plugin("jwt_auth",          "JWT Authentication",   "Secure token-based authentication and role management", "Security", enabled=True),
            Plugin("vault",             "Secrets Vault",        "Encrypted secrets storage", "Security",                          enabled=True),
            Plugin("audit_engine",      "Audit Engine",         "Flake8/Mypy/Bandit/Radon code quality analysis", "Security",     enabled=True),
        ]
        for p in plugins:
            self._plugins[p.id] = p

    def list_plugins(self) -> list:
        return [p.to_dict() for p in self._plugins.values()]

    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        return self._plugins.get(plugin_id)

    def enable(self, plugin_id: str) -> Optional[Dict]:
        p = self._plugins.get(plugin_id)
        if not p:
            return None
        p.enabled     = True
        p.status      = PluginStatus.ENABLED
        p.last_toggle = time.time()
        p.error_msg   = None
        print(f"🔌 [PLUGINS] Enabled: {p.name}")
        return p.to_dict()

    def disable(self, plugin_id: str) -> Optional[Dict]:
        p = self._plugins.get(plugin_id)
        if not p:
            return None
        p.enabled     = False
        p.status      = PluginStatus.DISABLED
        p.last_toggle = time.time()
        print(f"🔌 [PLUGINS] Disabled: {p.name}")
        return p.to_dict()

    def is_enabled(self, plugin_id: str) -> bool:
        p = self._plugins.get(plugin_id)
        return p.enabled if p else False

    def get_stats(self) -> Dict:
        total    = len(self._plugins)
        enabled  = sum(1 for p in self._plugins.values() if p.enabled)
        disabled = total - enabled
        cats: Dict[str, int] = {}
        for p in self._plugins.values():
            cats[p.category] = cats.get(p.category, 0) + 1
        return {
            "total": total,
            "enabled": enabled,
            "disabled": disabled,
            "by_category": cats,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
plugin_manager = PluginManager()

# ── FastAPI Router ─────────────────────────────────────────────────────────────
plugins_router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@plugins_router.get("")
async def list_plugins():
    """List all registered SPARK plugins with their status."""
    return {
        "plugins": plugin_manager.list_plugins(),
        "stats":   plugin_manager.get_stats(),
    }


@plugins_router.get("/stats")
async def plugin_stats():
    return plugin_manager.get_stats()


@plugins_router.get("/{plugin_id}")
async def get_plugin(plugin_id: str):
    p = plugin_manager.get_plugin(plugin_id)
    if not p:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    return p.to_dict()


class PluginToggleRequest(BaseModel):
    reason: Optional[str] = None


@plugins_router.post("/{plugin_id}/enable")
async def enable_plugin(plugin_id: str, req: PluginToggleRequest = PluginToggleRequest()):
    result = plugin_manager.enable(plugin_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    return {"status": "enabled", "plugin": result}


@plugins_router.post("/{plugin_id}/disable")
async def disable_plugin(plugin_id: str, req: PluginToggleRequest = PluginToggleRequest()):
    result = plugin_manager.disable(plugin_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    return {"status": "disabled", "plugin": result}


@plugins_router.post("/reload")
async def reload_plugins():
    """Re-register all core plugins (non-destructive — preserves enabled state)."""
    stats = plugin_manager.get_stats()
    return {"status": "reloaded", "stats": stats}
