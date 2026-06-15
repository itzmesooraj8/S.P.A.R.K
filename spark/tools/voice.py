"""Tools Voice — Stub implementations for STT/TTS."""

import logging

logger = logging.getLogger("spark.tools.voice")


def listen_and_transcribe(duration: int = 5) -> str | None:
    """Listen to microphone and transcribe speech."""
    try:
        import pyaudio
        import numpy as np

        chunk = 1024
        sample_rate = 16000

        p = pyaudio.PyAudio()
        stream = p.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=sample_rate,
            input=True,
            frames_per_buffer=chunk,
        )

        frames = []
        for _ in range(int(sample_rate / chunk * duration)):
            data = stream.read(chunk, exception_on_overflow=False)
            frames.append(data)

        stream.stop_stream()
        stream.close()
        p.terminate()

        audio_data = np.frombuffer(b"".join(frames), dtype=np.int16).astype(np.float32) / 32768.0

        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_data, language="en")
        return result.get("text", "")

    except ImportError as exc:
        logger.warning("Dependencies not installed for STT: %s", exc)
        return None
    except Exception as exc:
        logger.warning("STT failed: %s", exc)
        return None


async def speak(text: str) -> None:
    """Speak text using TTS."""
    try:
        import edge_tts
        import tempfile
        import os

        communicate = edge_tts.Communicate(text, "en-US-GuyNeural")
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            await communicate.save(f.name)
            tmp_path = f.name

        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(tmp_path)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                import time
                time.sleep(0.1)
            pygame.mixer.quit()
        except ImportError:
            os.system(f'start "" "{tmp_path}"')

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

    except ImportError:
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
        except ImportError:
            logger.warning("No TTS engine available")
