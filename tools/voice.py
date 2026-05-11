"""Voice utilities for TTS and optional Whisper-based microphone capture."""

from __future__ import annotations

import asyncio
import os
import tempfile

from audio.tts import SparkVoice

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


async def speak(text: str) -> str:
    voice = SparkVoice()
    await asyncio.to_thread(voice.speak, text)
    return "Speaking."


def load_whisper():
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
    try:
        model = load_whisper()
        wav_path = record_audio(duration)
        result = model.transcribe(wav_path)
        os.unlink(wav_path)
        return result.get("text", "").strip()
    except Exception as exc:
        return f""