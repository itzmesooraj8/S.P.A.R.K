"""
Mouth Module: Text-to-Speech using ElevenLabs or Edge-TTS (Free)
"""
import os
import asyncio
import io
import structlog
import sounddevice as sd
import numpy as np
import pydub
from core.config import settings

# --- Engines ---
# Lazy imports to avoid heavy dependencies if unused
try:
    from elevenlabs.client import ElevenLabs
except ImportError:
    ElevenLabs = None

try:
    import edge_tts
except ImportError:
    edge_tts = None

logger = structlog.get_logger()

# --- Config ---
VOICE_ID = "cgSgspJ2msm6clMCkdW9" # ElevenLabs specific
MODEL_ID = "eleven_multilingual_v2"

# Initializing Client if Key Exists (Optional)
eleven_client = None
if settings.secrets.elevenlabs_api_key and ElevenLabs:
    eleven_client = ElevenLabs(api_key=settings.secrets.elevenlabs_api_key.get_secret_value())

async def stream_speak(text):
    """
    Main entry point for streaming speech.
    Dispatches to the configured engine.
    """
    engine = settings.audio.engine.lower()
    voice = settings.audio.voice

    if engine == "elevenlabs":
        if not eleven_client:
            logger.warning("elevenlabs_key_missing_using_edge")
            # Fallback to Edge
            async for chunk in _stream_speak_edge(text, voice):
                yield chunk
        else:
            async for chunk in _stream_speak_eleven(text):
                yield chunk
    
    elif engine == "edge":
        async for chunk in _stream_speak_edge(text, voice):
            yield chunk
    
    else:
        logger.error("unknown_tts_engine", engine=engine)
        # Default fallback
        async for chunk in _stream_speak_edge(text, voice):
            yield chunk

async def _stream_speak_eleven(text):
    try:
        audio_gen = eleven_client.text_to_speech.convert(
            text=text,
            voice_id=VOICE_ID,
            model_id=MODEL_ID,
            output_format="mp3_44100_128",
        )
        # Convert generator to bytes
        if hasattr(audio_gen, '__iter__') and not isinstance(audio_gen, (bytes, bytearray)):
            audio_bytes = b"".join(audio_gen)
        else:
            audio_bytes = audio_gen
            
        audio_segment = pydub.AudioSegment.from_file(io.BytesIO(audio_bytes), format="mp3")
        # Normalize and yield
        pcm = np.array(audio_segment.get_array_of_samples(), dtype=np.float32) / 32768.0
        yield pcm, audio_segment.frame_rate
        
    except Exception as e:
        logger.error("elevenlabs_tts_failed", error=str(e))

async def _stream_speak_edge(text, voice="en-US-ChristopherNeural"):
    """
    Uses edge-tts to generate audio. 
    Note: edge-tts is async but usually writes to file or memory.
    We'll stream to memory.
    """
    if not edge_tts:
        logger.error("edge_tts_not_installed")
        return

    try:
        communicate = edge_tts.Communicate(text, voice)
        # EdgeTTS yields mp3 chunks. We need to buffer or process them.
        # Minimal latency approach: Join chunks into one stream for Pydub (MP3 frames are tricky to decode individually without context)
        # For true streaming, we'd need a streamable decoder. Pydub loads whole files.
        # Optimization: We accumulate briefly.
        
        mp3_buffer = b""
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_buffer += chunk["data"]
        
        if mp3_buffer:
             audio_segment = pydub.AudioSegment.from_file(io.BytesIO(mp3_buffer), format="mp3")
             pcm = np.array(audio_segment.get_array_of_samples(), dtype=np.float32) / 32768.0
             yield pcm, audio_segment.frame_rate

    except Exception as e:
        logger.error("edge_tts_failed", error=str(e))

async def play_streaming_audio(chunk_iter):
    """
    Play audio chunks.
    """
    async for pcm, sr in chunk_iter:
        if len(pcm) > 0:
            sd.play(pcm, sr, blocking=True)
            sd.stop()

def speak(text):
    """Synchronous wrapper for simple calls"""
    async def _run():
        async for pcm, sr in stream_speak(text):
             sd.play(pcm, sr, blocking=True)
    asyncio.run(_run())

if __name__ == "__main__":
    speak("System Online. Voice Upgrade Complete.")
