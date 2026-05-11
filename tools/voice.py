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


async def speak(text: str) -> None:
    """Speak text using EdgeTTS. Falls back to pyttsx3 if EdgeTTS fails."""
    if not text or not text.strip():
        return
    # Sanitize — remove markdown
    import re
    clean = re.sub(r'[*_`#\[\]()]', '', text)
    clean = re.sub(r'https?://\S+', 'link', clean)
    clean = clean[:500]  # cap length for TTS

    try:
        import edge_tts
        import tempfile, os
        communicate = edge_tts.Communicate(clean, voice="en-US-AriaNeural")
        tmp = tempfile.mktemp(suffix=".mp3")
        await communicate.save(tmp)
        # Play with pygame
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(tmp)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                await asyncio.sleep(0.1)
            pygame.mixer.music.unload()
        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass
    except Exception as e:
        # Fallback: pyttsx3 (offline, no internet needed)
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.setProperty('rate', 175)
            engine.say(clean)
            engine.runAndWait()
        except Exception as e2:
            print(f"[SPARK] TTS failed: {e} | fallback: {e2}")


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
    import asyncio
    asyncio.run(speak("SPARK voice system online. Audio confirmed."))