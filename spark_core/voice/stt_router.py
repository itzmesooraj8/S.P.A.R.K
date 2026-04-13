"""
SPARK Voice — STT Router
────────────────────────────────────────────────────────────────────────────────
Uses faster-whisper for local, GPU-accelerated speech-to-text transcription.

Endpoints exposed (registered in main.py):
  POST /api/voice/transcribe      — accept audio file → return transcribed text
  WebSocket /api/voice/transcribe/ws — stream audio chunks → stream back transcribed text
"""

import base64
import io
import json
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse

from voice.stt import whisper_stt

# ── Router ─────────────────────────────────────────────────────────────────────
stt_router = APIRouter(prefix="/api/voice", tags=["voice"])

def _audio_suffix(file: Optional[UploadFile]) -> str:
    if file and file.filename:
        ext = Path(file.filename).suffix.lower().strip()
        if ext:
            return ext

    if file and file.content_type:
        if "mpeg" in file.content_type or "mp3" in file.content_type:
            return ".mp3"
        if "ogg" in file.content_type:
            return ".ogg"
        if "wav" in file.content_type:
            return ".wav"

    return ".wav"


@stt_router.post("/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: Optional[str] = "en"
):
    """
    Transcribe uploaded audio file to text.
    
    Request:
        POST /api/voice/transcribe
        - file: audio file (WAV, MP3, etc.)
        - language: optional language code (default: "en")
    
    Response:
        {
            "text": "the transcribed text goes here",
            "language": "en"
        }
    """
    try:
        contents = await file.read()
        if not contents:
            return JSONResponse(
                {
                    "text": "",
                    "success": False,
                    "error": "No audio data received",
                },
                status_code=400,
            )

        transcript = await whisper_stt.transcribe_bytes(
            contents,
            suffix=_audio_suffix(file),
            language=language,
        )

        return JSONResponse({
            "text": transcript,
            "success": True,
            "language": language,
            "source": "faster-whisper-local",
        })
    
    except Exception as e:
        print(f"[STT] Transcription error: {e}")
        return JSONResponse(
            {
                "text": "",
                "success": False,
                "error": str(e)
            },
            status_code=500
        )


@stt_router.websocket("/transcribe/ws")
async def stt_websocket(websocket: WebSocket):
    """
    WebSocket STT channel for streaming transcription.
    
    Client sends binary audio chunks or JSON messages with audio base64.
    Server streams back transcription events.
    
    Message format:
        - Binary frames: raw audio PCM data
        - JSON: {"audio_b64": "...", "language": "en"}
    
    Server responds with:
        {"type": "buffering", "bytes_received": 12345}
        {"type": "final", "text": "...", "done": true}
    """
    await websocket.accept()

    try:
        audio_buffer = io.BytesIO()

        while True:
            try:
                # Receive either binary or text message
                data = await websocket.receive()

                if "bytes" in data:
                    # Binary audio chunk
                    audio_buffer.write(data["bytes"])
                    await websocket.send_json({
                        "type": "buffering",
                        "bytes_received": audio_buffer.tell()
                    })

                elif "text" in data:
                    msg = json.loads(data["text"])

                    if msg.get("action") == "reset":
                        audio_buffer = io.BytesIO()
                        await websocket.send_json({"type": "reset", "done": True})
                        continue

                    if msg.get("action") == "ping":
                        await websocket.send_json({"type": "pong"})
                        continue

                    if msg.get("audio_b64"):
                        try:
                            raw = base64.b64decode(msg.get("audio_b64") or "", validate=True)
                        except Exception:
                            await websocket.send_json({
                                "type": "error",
                                "message": "Invalid base64 payload",
                            })
                            continue

                        transcript = await whisper_stt.transcribe_bytes(
                            raw,
                            suffix=msg.get("suffix", ".wav"),
                            language=msg.get("language"),
                        )
                        await websocket.send_json({"type": "final", "text": transcript, "done": True})
                        continue

                    if msg.get("action") == "transcribe":
                        audio_buffer.seek(0)
                        audio_data = audio_buffer.getvalue()
                        if not audio_data:
                            await websocket.send_json({"type": "error", "message": "No audio data received"})
                            continue

                        suffix = msg.get("suffix") or ".wav"
                        transcript = await whisper_stt.transcribe_bytes(
                            audio_data,
                            suffix=suffix,
                            language=msg.get("language"),
                        )

                        await websocket.send_json({
                            "type": "final",
                            "text": transcript,
                            "done": True,
                        })

                        # Reset buffer for next recording cycle
                        audio_buffer = io.BytesIO()

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON in text frame"
                })
    
    except WebSocketDisconnect:
        print("[STT] WebSocket client disconnected")
    except Exception as e:
        print(f"[STT] WebSocket error: {e}")
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except Exception:
            pass
