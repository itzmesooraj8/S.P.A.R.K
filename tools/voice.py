"""Voice utilities for TTS and optional Whisper-based microphone capture."""

from __future__ import annotations

import asyncio
import os
import tempfile

try:
    import numpy as np
except Exception:  # pragma: no cover - optional dependency
    np = None

try:
    import sounddevice as sd
except Exception:  # pragma: no cover - optional dependency
    sd = None

try:
    import scipy.io.wavfile as wavfile
except Exception:  # pragma: no cover - optional dependency
    wavfile = None

try:
    import whisper
except Exception:  # pragma: no cover - optional dependency
    whisper = None

whisper_model = None


import asyncio, re, threading

def _speak_sync(text: str) -> None:
    """Synchronous TTS. Runs in a thread so it never blocks."""
    if not text or not text.strip():
        return
    # Strip markdown
    clean = re.sub(r'[*_`#\[\]()\-]+', ' ', text)
    clean = re.sub(r'https?://\S+', 'link', clean)
    clean = ' '.join(clean.split())[:400]
    if not clean:
        return
    
    # Try pyttsx3 first (offline, instant, no audio device issues)
    try:
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty('rate', 180)
        engine.setProperty('volume', 0.9)
        # Use a natural voice if available
        voices = engine.getProperty('voices')
        for voice in voices:
            if 'zira' in voice.name.lower() or 'david' in voice.name.lower():
                engine.setProperty('voice', voice.id)
                break
        engine.say(clean)
        engine.runAndWait()
        engine.stop()
        return
    except Exception as e1:
        pass
    
    # Fallback: EdgeTTS
    try:
        import edge_tts, tempfile, os
        import pygame
        
        async def _edge():
            communicate = edge_tts.Communicate(clean, voice="en-US-AriaNeural")
            tmp = tempfile.mktemp(suffix=".mp3")
            await communicate.save(tmp)
            return tmp
        
        tmp = asyncio.run(_edge())
        pygame.mixer.init()
        pygame.mixer.music.load(tmp)
        pygame.mixer.music.play()
        import time
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)
        pygame.mixer.music.unload()
        os.unlink(tmp)
    except Exception as e2:
        print(f"[SPARK TTS] Both engines failed: pyttsx3={e1}, edge={e2}")

async def speak(text: str) -> None:
    """Non-blocking async wrapper. Fire and forget."""
    thread = threading.Thread(target=_speak_sync, args=(text,), daemon=True)
    thread.start()


def load_whisper():
    """Load the Whisper base model once and reuse it."""
    global whisper_model
    if whisper is None:
        raise RuntimeError("openai-whisper is not installed")
    if whisper_model is None:
        whisper_model = whisper.load_model("base")
    return whisper_model


def record_audio(duration: int = 5, sample_rate: int = 16000) -> str:
    """Record from mic for `duration` seconds. Returns temp wav path."""
    if sd is None or np is None or wavfile is None:
        raise RuntimeError("audio recording dependencies are not installed")

    audio = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1, dtype="int16")
    sd.wait()
    fd, tmp = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    wavfile.write(tmp, sample_rate, audio)
    return tmp


def listen_and_transcribe(duration: int = 5) -> str:
    """Record audio and return transcribed text."""
    wav_path = ""
    try:
        wav_path = record_audio(duration)
        model = load_whisper()
        result = model.transcribe(wav_path, fp16=False)
        return result.get("text", "").strip()
    except Exception:
        return ""
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except Exception:
                pass

if __name__ == "__main__":
    _speak_sync("S.P.A.R.K voice system online. Audio confirmed.")