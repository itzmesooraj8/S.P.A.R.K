"""
SPARK Voice — TTS Router
────────────────────────────────────────────────────────────────────────────────
Primary engine: LuxTTS (local, 1 GB VRAM, 150× real-time speed) when CUDA is
available. Falls back to edge-tts (Microsoft Azure Neural Voices) automatically.

Engine selection at import time:
  1. VRAM ≥ 1 GB  → LuxTTS (high-quality prosody, low latency, fully offline)
  2. Fallback      → edge-tts (cloud, no GPU required)

Endpoints:
  POST /api/voice/speak       — synthesize text → streams MP3 audio
  GET  /api/voice/voices      — list available voices
  GET  /api/voice/engine      — which engine is active
  POST /api/voice/speak/ws    — WebSocket: receive text, stream back audio bytes
"""

import asyncio
import io
import json
import logging
import subprocess
import sys
from typing import Optional

import edge_tts
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

log = logging.getLogger(__name__)

# ── LuxTTS availability probe ──────────────────────────────────────────────────
def _probe_luxtts() -> bool:
    """Return True if LuxTTS is importable AND sufficient VRAM (≥1 GB) is available."""
    try:
        import torch  # type: ignore
        if not torch.cuda.is_available():
            return False
        vram_mb = torch.cuda.get_device_properties(0).total_memory // (1024 * 1024)
        if vram_mb < 1024:
            log.info("[TTS] VRAM %d MB < 1024 MB — using edge-tts fallback", vram_mb)
            return False
        import luxtts  # type: ignore  # noqa: F401
        log.info("[TTS] LuxTTS selected — VRAM: %d MB available", vram_mb)
        return True
    except Exception as exc:
        log.debug("[TTS] LuxTTS unavailable: %s", exc)
        return False

_LUXTTS_ACTIVE = _probe_luxtts()
TTS_ENGINE = "luxtts" if _LUXTTS_ACTIVE else "edge-tts"
print(f"🎙️  [TTS] Active engine: {TTS_ENGINE.upper()}")

# ── Router ─────────────────────────────────────────────────────────────────────
tts_router = APIRouter(prefix="/api/voice", tags=["voice"])

# SPARK default voice
DEFAULT_VOICE = "en-US-GuyNeural"
DEFAULT_RATE   = "+5%"
DEFAULT_PITCH  = "-10Hz"

# LuxTTS model name (high-quality male voice)
LUXTTS_VOICE   = "en_male_spark"


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = DEFAULT_VOICE
    rate: Optional[str] = DEFAULT_RATE
    pitch: Optional[str] = DEFAULT_PITCH


# ── LuxTTS synthesis ───────────────────────────────────────────────────────────
async def _synthesize_luxtts(text: str) -> bytes:
    """Run LuxTTS in a thread pool executor and return WAV/MP3 bytes."""
    import luxtts  # type: ignore
    loop = asyncio.get_event_loop()

    def _run() -> bytes:
        buf = io.BytesIO()
        luxtts.synthesize(text, voice=LUXTTS_VOICE, output_file=buf)
        buf.seek(0)
        return buf.read()

    return await loop.run_in_executor(None, _run)


# ── edge-tts synthesis ─────────────────────────────────────────────────────────
async def _synthesize_edgetts(text: str, voice: str, rate: str, pitch: str) -> bytes:
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()


async def _synthesize_bytes(text: str, voice: str, rate: str, pitch: str) -> bytes:
    """Unified synthesis — tries LuxTTS first, falls back to edge-tts."""
    if _LUXTTS_ACTIVE:
        try:
            return await _synthesize_luxtts(text)
        except Exception as exc:
            log.warning("[TTS] LuxTTS synthesis failed (%s) — falling back to edge-tts", exc)
    return await _synthesize_edgetts(text, voice, rate, pitch)


@tts_router.get("/engine")
async def get_engine():
    """Return which TTS engine is currently active."""
    return {"engine": TTS_ENGINE, "luxtts_active": _LUXTTS_ACTIVE}


@tts_router.post("/speak")
async def speak(req: SpeakRequest):
    """Synthesize text to speech and stream back MP3/WAV audio."""
    voice = req.voice or DEFAULT_VOICE
    rate  = req.rate  or DEFAULT_RATE
    pitch = req.pitch or DEFAULT_PITCH

    if _LUXTTS_ACTIVE:
        async def audio_stream():
            data = await _synthesize_luxtts(req.text)
            yield data
        media_type = "audio/wav"
    else:
        async def audio_stream():  # type: ignore[no-redef]
            communicate = edge_tts.Communicate(req.text, voice, rate=rate, pitch=pitch)
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        media_type = "audio/mpeg"

    return StreamingResponse(
        audio_stream(),
        media_type=media_type,
        headers={
            "Content-Disposition": "inline; filename=spark_speech.mp3",
            "Cache-Control": "no-cache",
            "X-Voice": LUXTTS_VOICE if _LUXTTS_ACTIVE else voice,
            "X-Engine": TTS_ENGINE,
        },
    )


@tts_router.get("/voices")
async def list_voices():
    """Return available voices filtered to English."""
    voices = await edge_tts.list_voices()
    english = [
        {
            "name": v["ShortName"],
            "display": v["FriendlyName"],
            "gender": v["Gender"],
            "locale": v["Locale"],
        }
        for v in voices
        if v["Locale"].startswith("en")
    ]
    return {"voices": english, "default": DEFAULT_VOICE}


@tts_router.websocket("/ws")
async def tts_websocket(websocket: WebSocket):
    """
    WebSocket TTS channel.
    Client sends: { "text": "...", "voice": "...", "rate": "...", "pitch": "..." }
    Server streams back raw audio bytes (binary frames) then sends JSON done frame.
    """
    await websocket.accept()
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                # Treat raw text as text to speak
                data = {"text": raw}

            text  = data.get("text", "")
            voice = data.get("voice", DEFAULT_VOICE)
            rate  = data.get("rate",  DEFAULT_RATE)
            pitch = data.get("pitch", DEFAULT_PITCH)

            if not text.strip():
                continue

            try:
                communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
                chunk_count = 0
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        await websocket.send_bytes(chunk["data"])
                        chunk_count += 1
                # Signal completion
                await websocket.send_text(
                    json.dumps({"type": "tts_done", "chunks": chunk_count})
                )
            except Exception as e:
                await websocket.send_text(
                    json.dumps({"type": "tts_error", "error": str(e)})
                )

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"⚠️ [TTS WS] Error: {e}")
