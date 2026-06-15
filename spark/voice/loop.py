"""Voice Loop — Always listening with wake word, beep, STT, TTS."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Coroutine
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger("spark.voice.loop")


class VoiceState(str, Enum):
    SLEEPING = "sleeping"
    LISTENING = "listening"
    PROCESSING = "processing"
    SPEAKING = "speaking"
    INTERRUPTED = "interrupted"


@dataclass
class VoiceTurn:
    role: str
    content: str
    timestamp: float = field(default_factory=time.time)
    is_interrupt: bool = False


class VoiceLoop:
    """
    Always-listening voice system.

    Flow:
    1. Listen for wake word ("Hey SPARK")
    2. Play beep sound
    3. Whisper STT transcribes speech
    4. SparkOS.process() handles the command
    5. pyttsx3 TTS speaks the response
    6. Back to listening
    """

    def __init__(self, wake_words: list[str] | None = None) -> None:
        self._wake_words = wake_words or ["hey spark", "spark", "jarvis"]
        self._state = VoiceState.SLEEPING
        self._conversation: list[VoiceTurn] = []
        self._max_context = 20
        self._stt_engine = None
        self._tts_engine = None
        self._on_process: Callable[[str], Coroutine[Any, Any, str]] | None = None
        self._running = False

    def initialize(self) -> None:
        try:
            from spark.audio.stt import SparkEars
            self._stt_engine = SparkEars()
            logger.info("Voice loop STT initialized")
        except Exception as exc:
            logger.warning("STT init failed: %s", exc)

        try:
            from spark.audio.tts import SparkVoice
            self._tts_engine = SparkVoice()
            logger.info("Voice loop TTS initialized")
        except Exception as exc:
            logger.warning("TTS init failed: %s", exc)

    def on_process(self, handler: Callable[[str], Coroutine[Any, Any, str]]) -> None:
        self._on_process = handler

    async def start(self) -> None:
        self._running = True
        self._state = VoiceState.SLEEPING
        logger.info("Voice loop started — listening for wake word")

        while self._running:
            try:
                if self._state == VoiceState.SLEEPING:
                    await self._listen_for_wake()
                elif self._state == VoiceState.LISTENING:
                    await self._listen_for_command()
                elif self._state == VoiceState.PROCESSING:
                    await asyncio.sleep(0.1)
                elif self._state == VoiceState.SPEAKING:
                    await asyncio.sleep(0.1)
                elif self._state == VoiceState.INTERRUPTED:
                    await self._handle_interrupt()
            except Exception as exc:
                logger.error("Voice loop error: %s", exc)
                await asyncio.sleep(0.5)

    def stop(self) -> None:
        self._running = False
        self._state = VoiceState.SLEEPING
        logger.info("Voice loop stopped")

    async def _listen_for_wake(self) -> None:
        text = await self._transcribe(duration=3)
        if text:
            text_lower = text.lower().strip()
            for wake_word in self._wake_words:
                if wake_word in text_lower:
                    logger.info("Wake word detected: %s", wake_word)
                    self._state = VoiceState.LISTENING
                    self._conversation.append(VoiceTurn(role="wake", content=text))
                    self._play_beep()
                    await self._speak("Yes, sir?")
                    return
        await asyncio.sleep(0.5)

    async def _listen_for_command(self) -> None:
        text = await self._transcribe(duration=5)
        if not text:
            return

        text_lower = text.lower().strip()

        interrupt_words = ["stop", "cancel", "actually", "nevermind", "never mind", "wait"]
        if any(w in text_lower for w in interrupt_words):
            logger.info("Interruption detected: %s", text)
            self._state = VoiceState.INTERRUPTED
            self._conversation.append(VoiceTurn(role="user", content=text, is_interrupt=True))
            return

        if any(w in text_lower for w in self._wake_words):
            self._conversation.append(VoiceTurn(role="user", content=text))
            self._play_beep()
            await self._speak("Yes, sir?")
            return

        self._conversation.append(VoiceTurn(role="user", content=text))
        self._state = VoiceState.PROCESSING

        if self._on_process:
            response = await self._on_process(text)
            if response:
                self._conversation.append(VoiceTurn(role="assistant", content=response))
                self._state = VoiceState.SPEAKING
                await self._speak(response)

        self._state = VoiceState.LISTENING

    async def _handle_interrupt(self) -> None:
        if self._tts_engine:
            try:
                self._tts_engine.stop()
            except Exception:
                pass
        self._state = VoiceState.LISTENING
        await self._speak("Stopped, sir.")

    def _play_beep(self) -> None:
        """Play a short beep to indicate listening."""
        try:
            import winsound
            winsound.Beep(1000, 200)
        except ImportError:
            try:
                import os
                os.system("printf '\\a'")
            except Exception:
                pass

    async def _transcribe(self, duration: int = 5) -> str:
        if self._stt_engine is None:
            return ""
        try:
            result = self._stt_engine.listen(duration)
            return result or ""
        except Exception as exc:
            logger.warning("Transcription failed: %s", exc)
            return ""

    async def _speak(self, text: str) -> None:
        if self._tts_engine is None or not text:
            return
        try:
            self._tts_engine.speak(text)
        except Exception as exc:
            logger.warning("Speech failed: %s", exc)

    def get_context(self, limit: int = 10) -> list[dict[str, Any]]:
        return [
            {"role": t.role, "content": t.content, "timestamp": t.timestamp}
            for t in self._conversation[-limit:]
        ]

    def state(self) -> str:
        return self._state.value

    def info(self) -> dict[str, Any]:
        return {
            "state": self._state.value,
            "wake_words": self._wake_words,
            "conversation_turns": len(self._conversation),
            "stt_available": self._stt_engine is not None,
            "tts_available": self._tts_engine is not None,
        }
