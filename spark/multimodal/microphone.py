"""Microphone Stream — Audio input for continuous listening."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("spark.multimodal.microphone")


class MicrophoneStream:
    """Continuous microphone input."""

    def __init__(self) -> None:
        self._active = False

    def start(self) -> bool:
        try:
            import pyaudio
            self._active = True
            logger.info("Microphone stream started")
            return True
        except ImportError:
            logger.warning("pyaudio not installed")
        return False

    def read_audio(self, duration: int = 5) -> bytes | None:
        if not self._active:
            return None
        try:
            import pyaudio
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=1024)
            frames = [stream.read(1024) for _ in range(int(16000 / 1024 * duration))]
            stream.stop_stream()
            stream.close()
            p.terminate()
            return b"".join(frames)
        except Exception as exc:
            logger.warning("Audio read failed: %s", exc)
        return None

    def stop(self) -> None:
        self._active = False
        logger.info("Microphone stream stopped")

    @property
    def is_active(self) -> bool:
        return self._active
