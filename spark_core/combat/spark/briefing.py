"""
SPARK Proactive Briefing Engine
==================================
Generates contextual spoken briefings using SPARK's local Ollama backend.
Briefings are timed (morning/evening/on-event) and mode-aware.

Voice:  Delivered via the TTS router (LuxTTS → edge-tts fallback).
Output: Structured JSON + plain text for rendering in the HUD status line.
"""
import asyncio
import json
import logging
import datetime
from typing import Optional

log = logging.getLogger(__name__)

_SPARK_SYSTEM = """You are SPARK — SPARK's proactive AI assistant.
You speak in brief, confident, informative sentences. No filler words.
You always:
  • Open with a time-aware greeting (Good morning / Afternoon / Evening)
  • Summarise the 2-3 most operationally relevant events
  • End with one actionable recommendation

Keep each briefing under 120 words. Use a calm, authoritative tone.
Respond ONLY with the briefing text — no markdown, no JSON wrapper.
"""


async def generate_briefing(
    mode: str = "PASSIVE",
    context: Optional[dict] = None,
    model: str = "llama3",
    ollama_url: str = "http://localhost:11434",
    speak: bool = True,
) -> dict:
    """
    Generate and optionally TTS-synthesise a SPARK briefing.

    context keys (all optional):
      active_threats, globe_events, system_status, operator_name,
      combat_active, time_override

    Returns {"text", "audio_url", "timestamp", "mode"}
    """
    now  = datetime.datetime.now()
    hour = now.hour
    if hour < 12:
        greeting_time = "morning"
    elif hour < 17:
        greeting_time = "afternoon"
    else:
        greeting_time = "evening"

    ctx = context or {}
    operator       = ctx.get("operator_name", "Commander")
    active_threats = ctx.get("active_threats", 0)
    globe_events   = ctx.get("globe_events", 0)
    sys_status     = ctx.get("system_status", "nominal")
    combat_active  = ctx.get("combat_active", mode == "COMBAT")

    user_prompt = (
        f"Good {greeting_time}.  It is {now.strftime('%H:%M')} on {now.strftime('%A, %d %B %Y')}.\n"
        f"Operator: {operator}\n"
        f"SPARK mode: {mode}\n"
        f"System status: {sys_status}\n"
        f"Active threat indicators: {active_threats}\n"
        f"Globe intelligence events (last hour): {globe_events}\n"
        + (f"Combat mode is ACTIVE.\n" if combat_active else "")
        + "\nGenerate a concise operational briefing."
    )

    text = ""
    try:
        import httpx
        payload = {
            "model":    model,
            "messages": [
                {"role": "system", "content": _SPARK_SYSTEM},
                {"role": "user",   "content": user_prompt},
            ],
            "stream": False,
        }
        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(f"{ollama_url}/api/chat", json=payload)
            res.raise_for_status()
            text = res.json().get("message", {}).get("content", "").strip()
    except Exception as exc:
        log.warning("SPARK LLM unavailable: %s", exc)
        text = (
            f"Good {greeting_time}, {operator}. "
            f"System status is {sys_status}. "
            f"{active_threats} active threat indicator{'s' if active_threats != 1 else ''} detected. "
            "All primary subsystems online. Standing by."
        )

    audio_url = ""
    if speak and text:
        try:
            audio_url = await _synthesize_briefing(text)
        except Exception as exc:
            log.warning("SPARK TTS failed: %s", exc)

    return {
        "text":      text,
        "audio_url": audio_url,
        "timestamp": now.isoformat(),
        "mode":      mode,
    }


async def _synthesize_briefing(text: str) -> str:
    """
    Submit text to the TTS router and return a data-URI for the audio.
    Returns empty string if TTS is unavailable.
    """
    try:
        import httpx
        async with httpx.AsyncClient(timeout=15) as client:
            res = await client.post(
                "http://localhost:8000/api/voice/speak",
                json={"text": text, "voice": "en-US-GuyNeural", "rate": "+5%", "pitch": "-5Hz"},
            )
            if res.status_code == 200:
                import base64
                b64 = base64.b64encode(res.content).decode()
                return f"data:audio/mpeg;base64,{b64}"
    except Exception:
        pass
    return ""


_scheduled_tasks: dict = {}


async def schedule_briefing(
    hour: int = 7,
    minute: int = 0,
    mode: str = "PASSIVE",
    context: Optional[dict] = None,
) -> str:
    """
    Schedule a daily briefing at the given local time.
    Returns job_id.
    """
    import uuid
    job_id = str(uuid.uuid4())[:8]

    async def _daily_loop():
        while True:
            now = datetime.datetime.now()
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += datetime.timedelta(days=1)
            wait_secs = (target - now).total_seconds()
            await asyncio.sleep(wait_secs)
            try:
                briefing = await generate_briefing(mode=mode, context=context)
                from spark_core.ws.manager import ws_manager
                await ws_manager.broadcast("ai", {
                    "type":    "SPARK_BRIEFING",
                    "briefing": briefing,
                })
            except Exception as exc:
                log.error("Scheduled briefing failed: %s", exc)

    task = asyncio.create_task(_daily_loop(), name=f"spark_briefing_{job_id}")
    _scheduled_tasks[job_id] = task
    log.info("SPARK daily briefing scheduled at %02d:%02d (job %s)", hour, minute, job_id)
    return job_id
