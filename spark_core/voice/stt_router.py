"""
SPARK Voice — STT Router
────────────────────────────────────────────────────────────────────────────────
Uses faster-whisper for local, GPU-accelerated speech-to-text transcription.

Endpoints exposed (registered in main.py):
  POST /api/voice/transcribe      — accept audio file → return transcribed text
  WebSocket /api/voice/transcribe/ws — stream audio chunks → stream back transcribed text
"""

import asyncio
import io
import json
from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Import the working Whisper model from audio module
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from audio.stt import SpeechToText

# ── Router ─────────────────────────────────────────────────────────────────────
stt_router = APIRouter(prefix="/api/voice", tags=["voice"])

# Initialize Whisper model once on startup
_stt_model = None

def get_stt_model():
    """Lazy-load STT model on first use to avoid startup slowdown."""
    global _stt_model
    if _stt_model is None:
        print("[STT] Loading Whisper model on first request...")
        _stt_model = SpeechToText()
    return _stt_model


class TranscribeRequest(BaseModel):
    """For batch transcription via REST."""
    language: Optional[str] = "en"


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
            "confidence": 0.95,
            "language": "en"
        }
    """
    try:
        # Read the audio file into memory
        contents = await file.read()
        
        # Save to temporary file (Whisper works best with files)
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name
        
        try:
            # Get or load the STT model in a thread to avoid blocking
            stt = get_stt_model()
            
            # Run transcription in thread pool (CPU-bound)
            loop = asyncio.get_event_loop()
            transcript = await loop.run_in_executor(
                None,
                stt.transcribe,
                tmp_path
            )
            
            return JSONResponse({
                "text": transcript,
                "success": True,
                "language": language,
                "source": f"faster-whisper-local"
            })
        finally:
            # Clean up temp file
            os.unlink(tmp_path)
    
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
        {"type": "transcribing", "partial": "..."}  (live partial)
        {"type": "final", "text": "...", "done": true}
    """
    await websocket.accept()
    
    try:
        stt = get_stt_model()
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
                    
                    if msg.get("action") == "transcribe":
                        # Client signals end of audio, transcribe the buffer
                        audio_buffer.seek(0)
                        audio_data = audio_buffer.getvalue()
                        
                        if not audio_data:
                            await websocket.send_json({
                                "type": "error",
                                "message": "No audio data received"
                            })
                            continue
                        
                        # Save buffer to temp file and transcribe
                        import tempfile
                        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                            tmp.write(audio_data)
                            tmp_path = tmp.name
                        
                        try:
                            loop = asyncio.get_event_loop()
                            transcript = await loop.run_in_executor(
                                None,
                                stt.transcribe,
                                tmp_path
                            )
                            
                            await websocket.send_json({
                                "type": "final",
                                "text": transcript,
                                "done": True
                            })
                        finally:
                            os.unlink(tmp_path)
                        
                        # Reset buffer for next recording
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
        except:
            pass
