from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Any

from core.memory_loop import write_turn


logger = logging.getLogger("SPARK_PERCEPTION")


_CONTEXT_KEYWORDS: dict[str, tuple[str, ...]] = {
    "coding": ("def ", "import ", "class ", "return ", "async", "function", "stack trace", "traceback"),
    "browsing": ("http", "www", "browser", "google", "search", "tab"),
    "email": ("inbox", "subject:", "regards", "forwarded", "reply", "outlook", "gmail"),
    "planning": ("meeting", "agenda", "schedule", "calendar", "reminder", "deadline"),
    "writing": ("document", "paragraph", "draft", "introduction", "conclusion"),
}


@dataclass(slots=True)
class AmbientContext:
    timestamp: float
    active: bool
    context_type: str = "unknown"
    active_window: str = "unknown"
    app_hint: str = "unknown"
    text_snippet: str = ""
    error: str = ""


class AmbientPerception:
    """Continuously captures lightweight screen context for prompt-time awareness."""

    def __init__(
        self,
        interval_seconds: int = 20,
        snippet_chars: int = 500,
        save_to_memory: bool = True,
    ) -> None:
        self.interval_seconds = max(5, int(interval_seconds))
        self.snippet_chars = max(120, int(snippet_chars))
        self.save_to_memory = save_to_memory
        self.current_context: AmbientContext = AmbientContext(timestamp=time.time(), active=False)
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._last_digest = ""

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="SPARK-Perception")
        self._thread.start()
        logger.info("Ambient perception daemon started (interval=%ss)", self.interval_seconds)

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def get_context_snapshot(self) -> dict[str, Any]:
        with self._lock:
            context = self.current_context
            return {
                "timestamp": context.timestamp,
                "active": context.active,
                "context_type": context.context_type,
                "active_window": context.active_window,
                "app_hint": context.app_hint,
                "text_snippet": context.text_snippet,
                "error": context.error,
            }

    def get_context_addendum(self, max_chars: int = 220) -> str:
        snapshot = self.get_context_snapshot()
        if not snapshot.get("active"):
            return ""

        snippet = str(snapshot.get("text_snippet") or "")[: max(80, int(max_chars))].strip()
        if snippet:
            snippet = snippet.replace("\n", " ")

        context_type = str(snapshot.get("context_type") or "unknown")
        active_window = str(snapshot.get("active_window") or "unknown")
        app_hint = str(snapshot.get("app_hint") or "unknown")

        return (
            "\n[AMBIENT CONTEXT] "
            f"Context={context_type}; Window={active_window}; App={app_hint}; "
            f"Snippet={snippet}"
        )

    def _loop(self) -> None:
        while self._running:
            try:
                context = self._capture_screen_context()
                with self._lock:
                    self.current_context = context
                self._persist_if_changed(context)
            except Exception as exc:
                logger.debug("Perception loop tick failed: %s", exc)
            time.sleep(self.interval_seconds)

    def _capture_screen_context(self) -> AmbientContext:
        try:
            import pyautogui
            import pytesseract

            tesseract_cmd = str(os.getenv("TESSERACT_CMD", "") or "").strip()
            if tesseract_cmd:
                pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

            screenshot = pyautogui.screenshot()
            downscale = int(os.getenv("SPARK_PERCEPTION_DOWNSCALE", "2") or "2")
            if downscale > 1:
                screenshot = screenshot.resize((max(1, screenshot.width // downscale), max(1, screenshot.height // downscale)))

            raw_text = pytesseract.image_to_string(screenshot)
            clean_text = " ".join(str(raw_text or "").split())
            context_type = self._classify_screen_context(clean_text)
            active_window = self._get_active_window_title()
            app_hint = self._infer_app_hint(active_window)

            return AmbientContext(
                timestamp=time.time(),
                active=True,
                context_type=context_type,
                active_window=active_window,
                app_hint=app_hint,
                text_snippet=clean_text[: self.snippet_chars],
            )
        except Exception as exc:
            return AmbientContext(
                timestamp=time.time(),
                active=False,
                error=str(exc),
            )

    def _classify_screen_context(self, text: str) -> str:
        normalized = text.lower()
        if not normalized.strip():
            return "general"

        scores: dict[str, int] = {}
        for context_type, keywords in _CONTEXT_KEYWORDS.items():
            score = sum(1 for token in keywords if token in normalized)
            if score > 0:
                scores[context_type] = score

        if not scores:
            return "general"
        return max(scores.items(), key=lambda item: item[1])[0]

    def _get_active_window_title(self) -> str:
        try:
            import pygetwindow as gw

            window = gw.getActiveWindow()
            title = str(window.title).strip() if window and getattr(window, "title", None) else "unknown"
            return title or "unknown"
        except Exception:
            return "unknown"

    def _infer_app_hint(self, active_window_title: str) -> str:
        lower = str(active_window_title or "").lower()
        if not lower or lower == "unknown":
            return "unknown"
        for hint in ("visual studio code", "chrome", "edge", "firefox", "outlook", "discord", "terminal", "powershell"):
            if hint in lower:
                return hint
        return lower.split("-")[-1].strip() if "-" in lower else lower[:40]

    def _persist_if_changed(self, context: AmbientContext) -> None:
        if not self.save_to_memory or not context.active:
            return

        digest_payload = f"{context.context_type}|{context.active_window}|{context.text_snippet[:120]}"
        digest = hashlib.sha1(digest_payload.encode("utf-8")).hexdigest()
        if digest == self._last_digest:
            return

        self._last_digest = digest
        try:
            compact = {
                "timestamp": context.timestamp,
                "context_type": context.context_type,
                "active_window": context.active_window,
                "app_hint": context.app_hint,
                "text_snippet": context.text_snippet[:200],
            }
            write_turn(
                "system",
                f"[ambient_context] {json.dumps(compact, ensure_ascii=False)}",
                metadata={"source": "ambient_perception", "context_type": context.context_type},
            )
        except Exception as exc:
            logger.debug("Failed to persist ambient context: %s", exc)


_perception: AmbientPerception | None = None
_perception_lock = threading.Lock()


def start_ambient_perception(interval_seconds: int | None = None) -> AmbientPerception:
    global _perception
    with _perception_lock:
        if _perception is None:
            configured_interval = int(os.getenv("SPARK_PERCEPTION_INTERVAL_SECONDS", str(interval_seconds or 20)))
            _perception = AmbientPerception(interval_seconds=configured_interval)
        _perception.start()
        return _perception


def stop_ambient_perception() -> None:
    global _perception
    with _perception_lock:
        if _perception is None:
            return
        _perception.stop()


def get_ambient_context_snapshot() -> dict[str, Any]:
    if _perception is None:
        return {"active": False}
    return _perception.get_context_snapshot()


def get_ambient_context_addendum(max_chars: int = 220) -> str:
    if _perception is None:
        return ""
    return _perception.get_context_addendum(max_chars=max_chars)
