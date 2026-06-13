"""Voice Loop — Always listening, understands interruptions, maintains context."""

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
    confidence: float = 0.0


class VoiceLoop:
    """
    Always-listening voice system.

    Tony Stark never types. The system is always listening:
    - Detects wake word
    - Streams transcription in real-time
    - Handles interruptions naturally
    - Maintains conversation context

    Example flow:
    User: "Jarvis"
    SPARK: "Yes, sir?"
    User: "Open my project"
    SPARK: *opens project*
    User: "No, the other one"
    SPARK: *switches to correct project*
    User: "Deploy it"
    SPARK: *deploys*
    User: "Actually stop"
    SPARK: *stops deployment*
    """

    def __init__(self, wake_words: list[str] | None = None) -> None:
        self._wake_words = wake_words or ["jarvis", "spark", "hey spark"]
        self._state = VoiceState.SLEEPING
        self._conversation: list[VoiceTurn] = []
        self._max_context = 20
        self._wake_threshold = 0.5
        self._stt_engine = None
        self._tts_engine = None
        self._on_process: Callable[[str], Coroutine[Any, Any, str]] | None = None
        self._on_wake: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._on_interrupt: Callable[[], Coroutine[Any, Any, None]] | None = None
        self._running = False
        self._last_voice_activity = 0.0
        self._silence_threshold = 2.0
        self._stream_buffer: list[str] = []

    def initialize(self) -> None:
        try:
            from spark.audio.stt import SparkEars
            self._stt_engine = SparkEars()
            logger.info("Voice loop STT initialized")
        except Exception as exc:
            logger.warning("STT init failed: %s", exc)

        try:
            from spark.audio.tts import SparkVoice
            self._tts_engine = SparkVoice({})
            logger.info("Voice loop TTS initialized")
        except Exception as exc:
            logger.warning("TTS init failed: %s", exc)

    def on_process(self, handler: Callable[[str], Coroutine[Any, Any, str]]) -> None:
        self._on_process = handler

    def on_wake(self, handler: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._on_wake = handler

    def on_interrupt(self, handler: Callable[[], Coroutine[Any, Any, None]]) -> None:
        self._on_interrupt = handler

    async def start(self) -> None:
        self._running = True
        self._state = VoiceState.LISTENING
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
                    if self._on_wake:
                        await self._on_wake()
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
            if self._on_interrupt:
                await self._on_interrupt()
            return

        if any(w in text_lower for w in self._wake_words):
            self._conversation.append(VoiceTurn(role="user", content=text))
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
            {"role": t.role, "content": t.content, "timestamp": t.timestamp, "is_interrupt": t.is_interrupt}
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
