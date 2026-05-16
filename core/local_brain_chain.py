"""
core/local_brain_chain.py — SPARK Local Brain Chain
=====================================================

3-model local fallback chain that activates automatically when Groq
is rate-limited, in cooldown, or unreachable.

Chain order:  gemma4  →  qwen2.5  →  qwen2.5:0.5b  (mini)
Each model is tried in sequence. If one fails or times out, the next
is tried. Only when ALL three fail does SPARK return an offline reply.

This module is intentionally self-contained. Import it anywhere and
call `local_chain_complete(messages)` — no global state needed.
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import time
from dataclasses import dataclass
from typing import Any

import requests

log = logging.getLogger("spark.local_brain_chain")

# ---------------------------------------------------------------------------
# Model definitions — ordered by capability (best first)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LocalModel:
    name: str                  # Ollama model tag
    timeout_seconds: float     # Per-request timeout
    description: str           # Human-readable label for logs/HUD

BRAIN_CHAIN: list[LocalModel] = [
    LocalModel(
        name=os.getenv("SPARK_LOCAL_PRIMARY",   "gemma4"),
        timeout_seconds=float(os.getenv("SPARK_LOCAL_PRIMARY_TIMEOUT",   "45")),
        description="Primary local brain (Gemma 4)",
    ),
    LocalModel(
        name=os.getenv("SPARK_LOCAL_SECONDARY", "qwen2.5"),
        timeout_seconds=float(os.getenv("SPARK_LOCAL_SECONDARY_TIMEOUT", "30")),
        description="Secondary local brain (Qwen 2.5)",
    ),
    LocalModel(
        name=os.getenv("SPARK_LOCAL_MINI",      "qwen2.5:0.5b"),
        timeout_seconds=float(os.getenv("SPARK_LOCAL_MINI_TIMEOUT",      "15")),
        description="Mini local brain (Qwen 2.5 0.5B)",
    ),
]

# ---------------------------------------------------------------------------
# Ollama connectivity
# ---------------------------------------------------------------------------

_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
_last_probe_time: float = 0.0
_probe_interval: float = 5.0          # Only probe every 5 seconds
_ollama_available: bool | None = None  # None = unknown


def _is_ollama_reachable() -> bool:
    """Quick TCP probe — does not make an HTTP request."""
    global _last_probe_time, _ollama_available

    now = time.time()
    if _ollama_available is not None and now - _last_probe_time < _probe_interval:
        return _ollama_available

    try:
        from urllib.parse import urlparse

        parsed = urlparse(_OLLAMA_HOST)
        host = parsed.hostname or "localhost"
        port = parsed.port or 11434
        with socket.create_connection((host, port), timeout=0.8):
            _ollama_available = True
    except OSError:
        _ollama_available = False

    _last_probe_time = now
    return bool(_ollama_available)


def _start_ollama() -> None:
    """Attempt to start the Ollama daemon if it is not running."""
    if _is_ollama_reachable():
        return
    log.info("Ollama not reachable — attempting to start daemon.")
    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        # Give it a moment to bind the port
        for _ in range(8):
            time.sleep(0.5)
            if _is_ollama_reachable():
                log.info("Ollama daemon started successfully.")
                return
        log.warning("Ollama daemon did not respond within 4 seconds.")
    except FileNotFoundError:
        log.warning("ollama binary not found. Install Ollama to enable local brain.")
    except Exception as exc:
        log.debug("Ollama start attempt failed: %s", exc)


def get_available_models() -> list[str]:
    """Return the list of model tags that Ollama currently has pulled."""
    try:
        resp = requests.get(f"{_OLLAMA_HOST}/api/tags", timeout=3)
        resp.raise_for_status()
        data = resp.json()
        models = data.get("models", []) if isinstance(data, dict) else []
        return [
            str(m.get("name") or m.get("model") or "")
            for m in models
            if isinstance(m, dict) and (m.get("name") or m.get("model"))
        ]
    except Exception:
        return []


def pull_model(model_name: str) -> bool:
    """
    Pull a model from Ollama registry if not already present.
    Runs synchronously — only called during setup/warm-up, not per request.
    Returns True on success.
    """
    available = get_available_models()
    if any(model_name in m for m in available):
        log.info("Model already available: %s", model_name)
        return True

    log.info("Pulling model %s — this may take a while...", model_name)
    try:
        result = subprocess.run(
            ["ollama", "pull", model_name],
            capture_output=True,
            text=True,
            timeout=600,   # 10 minute max for large models
        )
        if result.returncode == 0:
            log.info("Successfully pulled %s", model_name)
            return True
        log.warning("Pull failed for %s: %s", model_name, result.stderr[:200])
        return False
    except subprocess.TimeoutExpired:
        log.error("Pull timed out for %s", model_name)
        return False
    except Exception as exc:
        log.error("Pull error for %s: %s", model_name, exc)
        return False


# ---------------------------------------------------------------------------
# Single-model completion attempts (chat API then generate API)
# ---------------------------------------------------------------------------


def _try_chat(model: LocalModel, messages: list[dict[str, str]]) -> str | None:
    """Try the /api/chat endpoint. Returns text or None on failure."""
    try:
        resp = requests.post(
            f"{_OLLAMA_HOST}/api/chat",
            json={"model": model.name, "messages": messages, "stream": False},
            timeout=model.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            msg = data.get("message", {})
            content = str(msg.get("content", "") or "").strip()
            if content:
                return content
        return None
    except requests.exceptions.Timeout:
        log.debug("Chat timeout for %s (%.0fs)", model.name, model.timeout_seconds)
        return None
    except requests.exceptions.HTTPError as exc:
        status = getattr(exc.response, "status_code", None)
        if status == 404:
            log.debug("Model %s not found in Ollama", model.name)
        else:
            log.debug("Chat HTTP error for %s: %s", model.name, exc)
        return None
    except Exception as exc:
        log.debug("Chat error for %s: %s", model.name, exc)
        return None


def _try_generate(model: LocalModel, messages: list[dict[str, str]]) -> str | None:
    """Try the /api/generate endpoint as fallback. Returns text or None."""
    prompt = "\n\n".join(
        f"[{m.get('role', 'user').upper()}]\n{m.get('content', '').strip()}"
        for m in messages
        if m.get('content', '').strip()
    )
    try:
        resp = requests.post(
            f"{_OLLAMA_HOST}/api/generate",
            json={"model": model.name, "prompt": prompt, "stream": False},
            timeout=model.timeout_seconds,
        )
        resp.raise_for_status()
        data = resp.json()
        if isinstance(data, dict):
            content = str(data.get("response", "") or "").strip()
            if content:
                return content
        return None
    except requests.exceptions.Timeout:
        log.debug("Generate timeout for %s (%.0fs)", model.name, model.timeout_seconds)
        return None
    except Exception as exc:
        log.debug("Generate error for %s: %s", model.name, exc)
        return None


# ---------------------------------------------------------------------------
# Chain execution
# ---------------------------------------------------------------------------

@dataclass
class ChainResult:
    text: str
    model_used: str | None       # None means all models failed
    attempts: list[str]          # Models that were tried
    success: bool

    @property
    def from_local(self) -> bool:
        return self.success and self.model_used is not None


def local_chain_complete(
    messages: list[dict[str, str]],
    *,
    chain: list[LocalModel] | None = None,
    auto_start: bool = True,
    auto_pull: bool = False,          # Set True to auto-pull missing models
) -> ChainResult:
    """
    Run the local model chain and return the first successful response.

    Parameters
    ----------
    messages:    OpenAI-style message list [{"role": ..., "content": ...}]
    chain:       Override the default BRAIN_CHAIN (useful for testing)
    auto_start:  Attempt to start Ollama if it is not running
    auto_pull:   Pull missing models on demand (slow — off by default)

    Returns
    -------
    ChainResult with .text, .model_used, .success
    """
    chain = chain or BRAIN_CHAIN
    attempts: list[str] = []

    # Ensure Ollama is running
    if auto_start and not _is_ollama_reachable():
        _start_ollama()

    if not _is_ollama_reachable():
        log.warning("Ollama is not reachable — all local models unavailable.")
        return ChainResult(
            text=_offline_reply(messages),
            model_used=None,
            attempts=[],
            success=False,
        )

    available = get_available_models()

    for model in chain:
        # Check if the model is pulled
        is_pulled = any(model.name in m for m in available)

        if not is_pulled:
            if auto_pull:
                log.info("Auto-pulling %s...", model.name)
                if not pull_model(model.name):
                    log.info("Skipping %s — pull failed", model.name)
                    attempts.append(f"{model.name}:not_pulled")
                    continue
            else:
                log.info("Skipping %s — not pulled (set SPARK_LOCAL_AUTOPULL=1 to enable)", model.name)
                attempts.append(f"{model.name}:not_available")
                continue

        log.info("Trying %s (%s)...", model.name, model.description)
        attempts.append(model.name)

        # Try chat endpoint first, then generate
        result = _try_chat(model, messages) or _try_generate(model, messages)

        if result:
            log.info("Local brain responded via %s", model.name)
            return ChainResult(
                text=result,
                model_used=model.name,
                attempts=attempts,
                success=True,
            )

        log.info("Model %s did not produce a response — trying next.", model.name)

    # All models failed
    log.warning("All local models failed. Attempts: %s", attempts)
    return ChainResult(
        text=_offline_reply(messages),
        model_used=None,
        attempts=attempts,
        success=False,
    )


# ---------------------------------------------------------------------------
# Offline reply (last resort when every model fails)
# ---------------------------------------------------------------------------

def _offline_reply(messages: list[dict[str, str]]) -> str:
    """Best-effort deterministic reply when no model is available."""
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        "",
    )
    text = (last_user or "").strip().lower()

    if not text:
        return "All language model backends are currently unavailable, sir."

    greetings = {"hi", "hello", "hey", "hii", "yo", "good morning", "good afternoon", "good evening"}
    if text in greetings:
        return (
            "Good day, sir. Groq and all local models are currently offline. "
            "I can still run tools — just ask."
        )

    if any(word in text for word in ["time", "date", "clock"]):
        from datetime import datetime
        return f"It is currently {datetime.now().strftime('%I:%M %p on %A, %B %d, %Y')}."

    if any(word in text for word in ["status", "health", "system"]):
        try:
            from tools.sysmon import get_system_health
            return get_system_health()
        except Exception:
            pass

    return (
        "I am running in offline mode, sir. Groq is unavailable and all "
        "local Ollama models failed to respond. Tool-only commands still work."
    )


# ---------------------------------------------------------------------------
# Warm-up utility — call once at startup
# ---------------------------------------------------------------------------

def warmup_chain(chain: list[LocalModel] | None = None) -> dict[str, bool]:
    """
    Probe each model with a one-token ping to prime Ollama's model loader.
    Returns {model_name: is_ready} for each model in the chain.
    Call this in a background thread at startup — it can take 10–30 seconds
    the first time each model is loaded into VRAM.

    Example usage in api/server.py startup:
        import threading
        from core.local_brain_chain import warmup_chain
        threading.Thread(target=warmup_chain, daemon=True).start()
    """
    chain = chain or BRAIN_CHAIN
    results: dict[str, bool] = {}

    if not _is_ollama_reachable():
        _start_ollama()

    if not _is_ollama_reachable():
        log.warning("Warmup skipped — Ollama not reachable.")
        return {m.name: False for m in chain}

    ping_messages = [{"role": "user", "content": "hi"}]

    for model in chain:
        available = get_available_models()
        if not any(model.name in m for m in available):
            log.info("Warmup: %s not pulled — skipping", model.name)
            results[model.name] = False
            continue

        log.info("Warming up %s...", model.name)
        # Use a short timeout for the warmup ping
        fast_model = LocalModel(
            name=model.name,
            timeout_seconds=min(model.timeout_seconds, 20.0),
            description=model.description,
        )
        result = _try_chat(fast_model, ping_messages) or _try_generate(fast_model, ping_messages)
        ready = result is not None
        results[model.name] = ready
        log.info("Warmup %s: %s", model.name, "ready" if ready else "failed")

    return results


# ---------------------------------------------------------------------------
# Status report (for HUD / health endpoint)
# ---------------------------------------------------------------------------

def chain_status() -> dict[str, Any]:
    """
    Return a JSON-serialisable status dict for the HUD or /api/health endpoint.
    Does NOT make any model completion calls — just checks availability.
    """
    ollama_up = _is_ollama_reachable()
    available = get_available_models() if ollama_up else []

    models = []
    for model in BRAIN_CHAIN:
        pulled = any(model.name in m for m in available)
        models.append({
            "name": model.name,
            "description": model.description,
            "timeout_seconds": model.timeout_seconds,
            "pulled": pulled,
            "ready": ollama_up and pulled,
        })

    ready_count = sum(1 for m in models if m["ready"])

    return {
        "ollama_host": _OLLAMA_HOST,
        "ollama_reachable": ollama_up,
        "chain_length": len(BRAIN_CHAIN),
        "ready_count": ready_count,
        "fully_operational": ready_count == len(BRAIN_CHAIN),
        "models": models,
    }
