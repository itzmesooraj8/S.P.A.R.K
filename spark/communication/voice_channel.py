"""Voice Channel — Voice I/O communication."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.communication.voice")


class VoiceChannel:
    """Handles voice input and output."""

    def __init__(self) -> None:
        self._tts = None
        self._stt = None
        self._enabled = True

    def speak(self, text: str) -> bool:
        if not self._enabled or not text:
            return False
        try:
            from audio.tts import SparkVoice
            voice = SparkVoice({})
            import asyncio
            asyncio.run(voice.speak(text))
            return True
        except Exception as exc:
            logger.warning("Voice output failed: %s", exc)
            return False

    def listen(self, duration: int = 5) -> str:
        try:
            from audio.stt import SparkEars
            ears = SparkEars()
            result = ears.listen(duration)
            return result or ""
        except Exception as exc:
            logger.warning("Voice input failed: %s", exc)
            return ""

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False

    @property
    def is_enabled(self) -> bool:
        return self._enabled
