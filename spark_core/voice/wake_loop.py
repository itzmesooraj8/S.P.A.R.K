"""
SPARK wake loop: wake-word -> STT -> orchestrator ingress -> optional local TTS.

This is the always-on voice round-trip entrypoint for hands-free interaction.
"""

from __future__ import annotations

import asyncio
import io
import os
import sys
import time
import uuid
import wave
from dataclasses import dataclass
from typing import Any, Dict, Optional

from messaging.events import IngressSource
from messaging.ingress import ingress_service
from system.event_bus import event_bus
from voice.stt import whisper_stt
from voice.tts import local_tts
from voice.wakeword import get_wakeword_sensitivity
from ws.manager import ws_manager


@dataclass
class WakeLoopStatus:
    running: bool = False
    phase: str = "idle"
    queue_depth: int = 0
    last_wake_at_ms: Optional[int] = None
    last_transcript: str = ""
    last_reply: str = ""
    last_error: str = ""
    last_tts_engine: str = ""
    tts_progress: float = 0.0


class WakeLoop:
    def __init__(self):
        self.capture_seconds = max(1.0, float(os.getenv("SPARK_WAKE_CAPTURE_SECONDS", "5")))
        self.cooldown_seconds = max(0.5, float(os.getenv("SPARK_WAKE_COOLDOWN_SECONDS", "2.5")))
        self.reply_timeout_seconds = max(5.0, float(os.getenv("SPARK_WAKE_REPLY_TIMEOUT_SECONDS", "45")))
        self.voice_session_id = (os.getenv("SPARK_WAKE_SESSION_ID", "voice:wake") or "voice:wake")[:128]
        self.voice_user_id = (os.getenv("SPARK_WAKE_USER_ID", "voice.local") or "voice.local")[:128]

        self._status = WakeLoopStatus()
        self._queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue(maxsize=16)
        self._task: Optional[asyncio.Task] = None
        self._pending_replies: Dict[str, asyncio.Future[str]] = {}
        self._last_wake_monotonic = 0.0

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._status.running,
            "phase": self._status.phase,
            "queue_depth": self._queue.qsize(),
            "last_wake_at_ms": self._status.last_wake_at_ms,
            "last_transcript": self._status.last_transcript,
            "last_reply": self._status.last_reply,
            "last_error": self._status.last_error,
            "last_tts_engine": self._status.last_tts_engine,
            "tts_progress": round(self._status.tts_progress, 3),
            "wake_sensitivity": round(get_wakeword_sensitivity(), 3),
            "capture_seconds": self.capture_seconds,
            "voice_session_id": self.voice_session_id,
        }

    async def _emit_status(self):
        payload = {
            "v": 1,
            "type": "VOICE_STATUS",
            "ts": time.time() * 1000,
            **self.get_status(),
        }
        await ws_manager.broadcast_json(payload, "system")

    async def _set_phase(self, phase: str):
        self._status.phase = phase
        await self._emit_status()

    def start(self):
        if self._task and not self._task.done():
            return
        self._status.running = True
        self._task = asyncio.create_task(self._run(), name="spark_wake_loop")
        print("[WakeLoop] Started")

    def stop(self):
        self._status.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        for turn_id, future in list(self._pending_replies.items()):
            if not future.done():
                future.cancel()
            self._pending_replies.pop(turn_id, None)
        print("[WakeLoop] Stopped")

    async def enqueue_wake(self, payload: Dict[str, Any]):
        if not self._status.running:
            return
        now = time.monotonic()
        if (now - self._last_wake_monotonic) < self.cooldown_seconds:
            return
        self._last_wake_monotonic = now
        self._status.last_wake_at_ms = int(time.time() * 1000)

        if self._queue.full():
            try:
                self._queue.get_nowait()
            except asyncio.QueueEmpty:
                pass

        await self._queue.put(payload or {})
        self._status.queue_depth = self._queue.qsize()
        await self._emit_status()

    async def ingest_assistant_reply(self, payload: Dict[str, Any]):
        if not isinstance(payload, dict):
            return
        metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
        turn_id = str(metadata.get("wake_loop_turn_id") or "").strip()
        if not turn_id:
            return

        future = self._pending_replies.get(turn_id)
        if not future or future.done():
            return

        text = str(payload.get("text") or "").strip()
        future.set_result(text)

    async def _run(self):
        await self._set_phase("idle")

        while self._status.running:
            try:
                wake_payload = await self._queue.get()
                self._status.queue_depth = self._queue.qsize()
                await self._handle_wake(wake_payload)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                self._status.last_error = str(exc)
                print(f"[WakeLoop] Error: {exc}")
                await self._set_phase("idle")

    async def _handle_wake(self, wake_payload: Dict[str, Any]):
        wake_confidence = float(wake_payload.get("confidence") or 0)
        wake_word = str(wake_payload.get("wake_word") or "wake-word")

        self._status.last_error = ""
        self._status.last_transcript = ""
        self._status.tts_progress = 0.0
        await self._set_phase("listening")

        try:
            transcript = await whisper_stt.transcribe_microphone(duration_sec=self.capture_seconds)
        except Exception as exc:
            self._status.last_error = f"STT failed: {exc}"
            await self._set_phase("idle")
            return

        transcript = (transcript or "").strip()
        if not transcript:
            self._status.last_error = "No speech recognized"
            await self._set_phase("idle")
            return

        self._status.last_transcript = transcript
        await self._set_phase("thinking")

        turn_id = str(uuid.uuid4())
        loop = asyncio.get_running_loop()
        future: asyncio.Future[str] = loop.create_future()
        self._pending_replies[turn_id] = future

        try:
            await ingress_service.ingest_text(
                content=transcript,
                source=IngressSource.INTERNAL,
                user_id=self.voice_user_id,
                conversation_id=self.voice_session_id,
                channel="voice",
                metadata={
                    "transport": "wake_loop",
                    "wake_word": wake_word,
                    "wake_confidence": round(wake_confidence, 3),
                    "wake_loop_turn_id": turn_id,
                },
            )

            reply_text = await asyncio.wait_for(future, timeout=self.reply_timeout_seconds)
        except asyncio.TimeoutError:
            self._status.last_error = "Timed out waiting for assistant reply"
            await self._set_phase("idle")
            return
        except Exception as exc:
            self._status.last_error = f"Ingress failed: {exc}"
            await self._set_phase("idle")
            return
        finally:
            self._pending_replies.pop(turn_id, None)

        reply_text = (reply_text or "").strip()
        if not reply_text:
            self._status.last_error = "Assistant returned empty reply"
            await self._set_phase("idle")
            return

        self._status.last_reply = reply_text
        await self._set_phase("speaking")
        await self._speak(reply_text)
        await self._set_phase("idle")

    async def _speak(self, text: str):
        try:
            audio_bytes, media_type, engine = await local_tts.synthesize(text)
            self._status.last_tts_engine = engine
        except Exception as exc:
            self._status.last_error = f"TTS failed: {exc}"
            self._status.tts_progress = 0.0
            await self._emit_status()
            return

        # If local playback is not possible, still mark completion for HUD visibility.
        if media_type != "audio/wav" or sys.platform != "win32":
            self._status.tts_progress = 1.0
            await self._emit_status()
            return

        duration_ms = _wav_duration_ms(audio_bytes)
        progress_task: Optional[asyncio.Task] = None
        if duration_ms > 0:
            progress_task = asyncio.create_task(self._run_tts_progress(duration_ms))

        try:
            await asyncio.to_thread(_play_wav_windows, audio_bytes)
        except Exception as exc:
            self._status.last_error = f"Audio playback failed: {exc}"
        finally:
            if progress_task:
                progress_task.cancel()
            self._status.tts_progress = 1.0
            await self._emit_status()

    async def _run_tts_progress(self, duration_ms: float):
        started = time.monotonic()
        while self._status.phase == "speaking":
            elapsed_ms = (time.monotonic() - started) * 1000.0
            progress = min(1.0, elapsed_ms / max(1.0, duration_ms))
            self._status.tts_progress = progress
            await self._emit_status()
            if progress >= 1.0:
                break
            await asyncio.sleep(0.2)


def _wav_duration_ms(audio_bytes: bytes) -> float:
    try:
        with wave.open(io.BytesIO(audio_bytes), "rb") as wav_file:
            frames = wav_file.getnframes()
            frame_rate = wav_file.getframerate() or 1
            return (frames / frame_rate) * 1000.0
    except Exception:
        return 0.0


def _play_wav_windows(audio_bytes: bytes):
    import winsound

    winsound.PlaySound(audio_bytes, winsound.SND_MEMORY)


wake_loop = WakeLoop()


@event_bus.subscribe("wake_word_detected")
async def _wake_word_event(payload: Dict[str, Any]):
    await wake_loop.enqueue_wake(payload or {})


@event_bus.subscribe("assistant_reply")
async def _assistant_reply_event(payload: Dict[str, Any]):
    await wake_loop.ingest_assistant_reply(payload or {})


def start_wake_loop():
    wake_loop.start()


def stop_wake_loop():
    wake_loop.stop()
