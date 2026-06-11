"""S.P.A.R.K. API Chat and Voice Interface Router with User Context binding."""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
import uuid
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from api.routes.auth import get_current_user_payload
from security.session_authorization import active_user_var

logger = logging.getLogger("SPARK_CHAT_ROUTES")

router = APIRouter(tags=["chat"])

# Rate limiting state
request_counts: defaultdict[str, list[float]] = defaultdict(list)


async def rate_limit(request: Request):
    """Simple sliding-window rate limiter (60 requests per minute)."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    request_counts[ip] = [ts for ts in request_counts[ip] if now - ts < 60]
    if len(request_counts[ip]) >= 60:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    request_counts[ip].append(now)


# Pydantic Domain Models
class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


def _bind_user_context(user: Any) -> None:
    """Extract and bind AuthenticatedUser/AuthTokenPayload details to ContextVar."""
    if not user:
        return
    username = getattr(user, "subject", None) or getattr(user, "username", None) or "unknown"
    role = getattr(user, "role", "viewer")
    permissions = list(getattr(user, "permissions", []) or [])
    active_user_var.set({
        "username": username,
        "role": role,
        "permissions": permissions,
    })


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(rate_limit)])
async def chat_endpoint(request: ChatRequest, user: Any = Depends(get_current_user_payload)):
    """Sends a chat message to S.P.A.R.K.'s brain (binds user context for tool RBAC)."""
    logger.info("chat_endpoint: direct brain path entered")
    _bind_user_context(user)
    try:
        from core.brain_entry import ask_spark_brain

        result = await ask_spark_brain(request.message, session_history=[])
        return ChatResponse(response=str(result.get("reply", "")).strip())
    except Exception as exc:
        logger.error("Chat endpoint failed: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": "chat_failed",
                "response": "I’m having trouble reaching the language model right now. Please try again in a moment.",
            },
        )


@router.post("/listen", dependencies=[Depends(rate_limit)])
async def listen_endpoint(user: Any = Depends(get_current_user_payload)):
    """Instructs S.P.A.R.K. to listen to local microphone input and process it under user context."""
    _bind_user_context(user)
    from audio.stt import SparkEars
    from core.brain_entry import ask_spark_brain
    from tools.voice import speak

    ears = SparkEars()
    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(None, ears.listen, 5)
    if not text:
        return {"error": "No speech detected"}

    result = await ask_spark_brain(text, session_history=[])
    await speak(result["reply"])
    result["transcript"] = text
    return result


@router.post("/voice-chat", dependencies=[Depends(rate_limit)])
async def voice_chat_endpoint(audio: UploadFile = File(...), user: Any = Depends(get_current_user_payload)):
    """Transcribes an uploaded WebM/WAV audio stream and responds under user context."""
    _bind_user_context(user)
    temp_audio_path = ""
    temp_response_path = ""
    try:
        from core.brain_entry import ask_spark_brain

        filename = audio.filename or ""
        raw_suffix = os.path.splitext(filename)[1] or ".webm"

        # Sanitize suffix
        suffix = "".join(c for c in raw_suffix if c.isalnum() or c == ".")
        if not suffix.startswith("."):
            suffix = "." + suffix
        suffix = suffix[:10]

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            temp_audio_path = tmp.name
            tmp.write(await audio.read())

        loop = asyncio.get_running_loop()

        def _transcribe() -> str:
            from tools.voice import load_whisper

            model = load_whisper()
            result = model.transcribe(temp_audio_path, fp16=False)
            return str(result.get("text", "")).strip()

        text = await loop.run_in_executor(None, _transcribe)
        if not text:
            return JSONResponse(status_code=400, content={"error": "no_speech_detected"})

        result = await ask_spark_brain(text, session_history=[])
        reply_text = str(result.get("reply", "")).strip()

        audio_url = ""
        try:
            from edge_tts import Communicate

            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            static_dir = os.path.join(base_dir, "api", "static")
            audio_dir = os.path.join(static_dir, "audio")
            os.makedirs(audio_dir, exist_ok=True)
            file_name = f"voice-{uuid.uuid4().hex}.mp3"
            temp_response_path = os.path.join(audio_dir, file_name)

            communicate = Communicate(reply_text or "", voice="en-US-AriaNeural")
            await communicate.save(temp_response_path)
            audio_url = f"/static/audio/{file_name}"
        except Exception as tts_exc:
            logger.info("TTS generation skipped or failed: %s", tts_exc)

        return {
            "text": text,
            "response": reply_text,
            "audio_url": audio_url,
        }
    except Exception as exc:
        logger.error("voice_chat endpoint failed: %s", exc, exc_info=True)
        return JSONResponse(status_code=500, content={"error": "voice_chat_failed", "message": str(exc)})
    finally:
        for path in (temp_audio_path, temp_response_path):
            if path and os.path.exists(path) and not path.endswith(".mp3"):
                try:
                    os.remove(path)
                except OSError:
                    pass
