"""Voice Engine — Unified voice I/O."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.voice")


class VoiceEngine:
    """Unified voice input/output engine."""

    def __init__(self) -> None:
        self._stt = None
        self._tts = None
        self._wake_word = None
        self._active = False

    def initialize(self) -> None:
        try:
            from audio.stt import SparkEars
            from audio.tts import SparkVoice
            self._stt = SparkEars()
            self._tts = SparkVoice({})
            logger.info("Voice engine initialized")
        except Exception as exc:
            logger.warning("Voice init failed: %s", exc)

    def listen(self, duration: int = 5) -> str:
        if self._stt is None:
            return ""
        try:
            result = self._stt.listen(duration)
            return result or ""
        except Exception as exc:
            logger.warning("Listen failed: %s", exc)
            return ""

    def speak(self, text: str) -> bool:
        if self._tts is None or not text:
            return False
        try:
            self._tts.speak(text)
            return True
        except Exception as exc:
            logger.warning("Speak failed: %s", exc)
            return False

    def stop(self) -> None:
        if self._tts:
            try:
                self._tts.stop()
            except Exception:
                pass

    def start_wake_word(self) -> None:
        try:
            from core.wake_word import start_wake_engine
            start_wake_engine()
            self._active = True
            logger.info("Wake word engine started")
        except Exception as exc:
            logger.warning("Wake word start failed: %s", exc)

    def stop_wake_word(self) -> None:
        try:
            from core.wake_word import stop_wake_engine
            stop_wake_engine()
            self._active = False
        except Exception:
            pass

    @property
    def is_active(self) -> bool:
        return self._active

    def info(self) -> dict[str, Any]:
        return {
            "stt_available": self._stt is not None,
            "tts_available": self._tts is not None,
            "active": self._active,
        }
