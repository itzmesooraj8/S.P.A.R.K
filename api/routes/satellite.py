from __future__ import annotations

import base64
import os
import tempfile
import logging
import uuid
import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from security.signature_verifier import verify_remote_request
from core.brain_entry import ask_spark_brain
from tools.voice import load_whisper

logger = logging.getLogger(__name__)
router = APIRouter()

class SatelliteRequest(BaseModel):
    payload: dict[str, Any]
    signature: str

@router.post("/api/satellite/command")
async def satellite_command(request: SatelliteRequest):
    """
    Secure Satellite endpoint.
    Verifies payload signature & timestamp, processes command (supports text/voice),
    runs it through SPARK Brain, and returns base64-encoded audio TTS response.
    """
    # 1. Verify Signature & Drift
    if not verify_remote_request(request.payload, request.signature):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid signature or timestamp drift")

    # 2. Extract input text or audio
    from security.session_authorization import active_user_var
    active_user_var.set({
        "username": "satellite",
        "role": "operator",
        "permissions": ["chat", "tools"],
    })
    payload = request.payload
    input_text = str(payload.get("text") or "").strip()
    audio_b64 = payload.get("audio")

    # If audio is sent, transcribe it using Whisper
    if audio_b64 and not input_text:
        try:
            audio_bytes = base64.b64decode(audio_b64)
            # Write to a secure NamedTemporaryFile
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(audio_bytes)
                temp_path = tmp_file.name

            # Run whisper transcription in thread pool
            loop = asyncio.get_running_loop()
            def _transcribe() -> str:
                model = load_whisper()
                result = model.transcribe(temp_path, fp16=False)
                return str(result.get("text", "")).strip()

            input_text = await loop.run_in_executor(None, _transcribe)
        except Exception as exc:
            logger.error(f"Whisper transcription failed: {exc}", exc_info=True)
            raise HTTPException(status_code=400, detail=f"Failed to process voice command: {exc}")
        finally:
            if 'temp_path' in locals() and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    if not input_text:
        raise HTTPException(status_code=400, detail="Empty command prompt received.")

    # 3. Route to Spark Brain
    try:
        result = await ask_spark_brain(input_text, session_history=[])
        reply = str(result.get("reply", "")).strip()
        tool_used = result.get("tool_used")
        tool_result = result.get("tool_result")
    except Exception as exc:
        logger.error(f"Spark Brain execution failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal processing error")

    # 4. Generate Edge-TTS response if possible
    response_audio_b64 = ""
    try:
        from edge_tts import Communicate
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_out:
            out_path = tmp_out.name

        communicate = Communicate(reply or "", voice="en-US-AriaNeural")
        await communicate.save(out_path)

        with open(out_path, "rb") as f:
            response_audio_b64 = base64.b64encode(f.read()).decode("utf-8")
    except Exception as tts_exc:
        logger.info("Satellite TTS generation skipped or failed: %s", tts_exc)
    finally:
        if 'out_path' in locals() and os.path.exists(out_path):
            try:
                os.remove(out_path)
            except OSError:
                pass

    return {
        "reply": reply,
        "tool_used": tool_used,
        "tool_result": str(tool_result) if tool_result is not None else None,
        "audio_response": response_audio_b64
    }
