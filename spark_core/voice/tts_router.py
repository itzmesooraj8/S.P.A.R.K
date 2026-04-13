"""
SPARK Voice — TTS Router
────────────────────────────────────────────────────────────────────────────────
Primary engine: Piper (local, offline).
Fallback engine: edge-tts.

Endpoints:
    POST /api/voice/speak       — synthesize text → streams audio
  GET  /api/voice/voices      — list available voices
  GET  /api/voice/engine      — which engine is active
    WebSocket /api/voice/ws     — receive text, stream back audio bytes
"""

import json
import logging
from typing import Optional

import edge_tts
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from voice.tts import local_tts

log = logging.getLogger(__name__)

# ── Router ─────────────────────────────────────────────────────────────────────
tts_router = APIRouter(prefix="/api/voice", tags=["voice"])

DEFAULT_VOICE = "en-US-GuyNeural"
DEFAULT_RATE = "+0%"
DEFAULT_PITCH = "+0Hz"


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = DEFAULT_VOICE
    rate: Optional[str] = DEFAULT_RATE
    pitch: Optional[str] = DEFAULT_PITCH

@tts_router.get("/engine")
async def get_engine():
    """Return which TTS engine is currently active."""
    return local_tts.get_engine_status()


@tts_router.post("/speak")
async def speak(req: SpeakRequest):
    """Synthesize text to speech and stream back audio."""
    voice = req.voice or DEFAULT_VOICE
    rate = req.rate or DEFAULT_RATE
    pitch = req.pitch or DEFAULT_PITCH

    try:
        data, media_type, engine = await local_tts.synthesize(
            text=req.text,
            voice=voice,
            rate=rate,
            pitch=pitch,
        )
    except Exception as exc:
        return StreamingResponse(
            iter([f"TTS synthesis failed: {exc}".encode("utf-8")]),
            status_code=500,
            media_type="text/plain",
        )

    async def audio_stream():
        yield data

    return StreamingResponse(
        audio_stream(),
        media_type=media_type,
        headers={
            "Content-Disposition": "inline; filename=spark_speech.mp3",
            "Cache-Control": "no-cache",
            "X-Voice": voice,
            "X-Engine": engine,
        },
    )


@tts_router.get("/voices")
async def list_voices():
    """Return available edge-tts voices and local defaults."""
    english = []
    try:
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
    except Exception as exc:
        log.warning("[TTS] Failed to list edge-tts voices: %s", exc)

    return {
        "voices": english,
        "default": DEFAULT_VOICE,
        "engines": local_tts.get_engine_status(),
    }


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

            text = data.get("text", "")
            voice = data.get("voice", DEFAULT_VOICE)
            rate = data.get("rate", DEFAULT_RATE)
            pitch = data.get("pitch", DEFAULT_PITCH)

            if not text.strip():
                continue

            try:
                audio_bytes, _, engine = await local_tts.synthesize(
                    text=text,
                    voice=voice,
                    rate=rate,
                    pitch=pitch,
                )
                await websocket.send_bytes(audio_bytes)
                await websocket.send_text(
                    json.dumps({
                        "type": "tts_done",
                        "chunks": 1,
                        "bytes": len(audio_bytes),
                        "engine": engine,
                    })
                )
            except Exception as e:
                await websocket.send_text(json.dumps({"type": "tts_error", "error": str(e)}))

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[TTS WS] Error: {e}")
