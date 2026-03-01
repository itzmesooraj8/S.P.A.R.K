"""
SPARK Voice — TTS Router
────────────────────────────────────────────────────────────────────────────────
Uses edge-tts (Microsoft Azure Neural Voices via free public API) to synthesize
speech for SPARK's verbal responses.

Endpoints exposed (registered in main.py):
  POST /api/voice/speak       — synthesize text → streams MP3 audio
  GET  /api/voice/voices      — list available edge-tts voices
  POST /api/voice/speak/ws    — WebSocket: receive text, stream back audio bytes
"""

import asyncio
import io
import json
from typing import Optional

import edge_tts
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# ── Router ─────────────────────────────────────────────────────────────────────
tts_router = APIRouter(prefix="/api/voice", tags=["voice"])

# SPARK default voice — professional, neutral, slightly synthetic = Jarvis vibes
DEFAULT_VOICE = "en-US-GuyNeural"
DEFAULT_RATE   = "+5%"   # slightly faster
DEFAULT_PITCH  = "-10Hz" # slightly deeper


class SpeakRequest(BaseModel):
    text: str
    voice: Optional[str] = DEFAULT_VOICE
    rate: Optional[str] = DEFAULT_RATE
    pitch: Optional[str] = DEFAULT_PITCH


async def _synthesize_bytes(text: str, voice: str, rate: str, pitch: str) -> bytes:
    """Run edge-tts synthesis and return raw MP3 bytes."""
    communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
    buf = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])
    buf.seek(0)
    return buf.read()


@tts_router.post("/speak")
async def speak(req: SpeakRequest):
    """
    Synthesize text to speech and stream back MP3 audio.
    Frontend can play this via:
        const audio = new Audio(URL.createObjectURL(blob));  audio.play();
    """
    voice = req.voice or DEFAULT_VOICE
    rate  = req.rate  or DEFAULT_RATE
    pitch = req.pitch or DEFAULT_PITCH

    async def audio_stream():
        communicate = edge_tts.Communicate(req.text, voice, rate=rate, pitch=pitch)
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]

    return StreamingResponse(
        audio_stream(),
        media_type="audio/mpeg",
        headers={
            "Content-Disposition": "inline; filename=spark_speech.mp3",
            "Cache-Control": "no-cache",
            "X-Voice": voice,
        },
    )


@tts_router.get("/voices")
async def list_voices():
    """Return available edge-tts voices filtered to English."""
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
