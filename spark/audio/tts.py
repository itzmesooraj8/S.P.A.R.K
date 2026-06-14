"""TTS — Text-to-Speech using edge-tts or pyttsx3 fallback."""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

logger = logging.getLogger("spark.audio.tts")


class SparkVoice:
    """Text-to-Speech with edge-tts primary and pyttsx3 fallback."""

    def __init__(self) -> None:
        self._engine = None

    def speak(self, text: str) -> None:
        """Speak text synchronously."""
        if not text:
            return

        try:
            self._speak_edge(text)
        except Exception:
            try:
                self._speak_pyttsx3(text)
            except Exception as exc:
                logger.warning("TTS failed: %s", exc)

    def _speak_edge(self, text: str) -> None:
        """Use edge-tts for high-quality speech."""
        try:
            import edge_tts
            import tempfile
            import os

            async def _generate():
                communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
                with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
                    await communicate.save(f.name)
                    return f.name

            tmp_path = asyncio.run(_generate())

            try:
                import pygame
                pygame.mixer.init()
                pygame.mixer.music.load(tmp_path)
                pygame.mixer.music.play()
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)
                pygame.mixer.quit()
            except ImportError:
                os.system(f'start "" "{tmp_path}"')

            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        except ImportError:
            raise ImportError("edge-tts not installed: pip install edge-tts")

    def _speak_pyttsx3(self, text: str) -> None:
        """Fallback to pyttsx3."""
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except ImportError:
            raise ImportError("pyttsx3 not installed: pip install pyttsx3")

    def stop(self) -> None:
        """Stop current speech."""
        try:
            import pygame
            if pygame.mixer.get_init():
                pygame.mixer.music.stop()
        except Exception:
            pass
