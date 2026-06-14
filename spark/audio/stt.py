"""STT — Speech-to-Text with Whisper and hallucination filtering."""

import logging
import os
import tempfile
from typing import Any

logger = logging.getLogger("spark.audio.stt")

WHISPER_HALLUCINATIONS = {
    "thank you for watching",
    "thank you for watching.",
    "thank you for watching!",
    "thanks for watching",
    "thanks for watching.",
    "thanks for watching!",
    "subscribe to my channel",
    "subscribe to the channel",
    "please subscribe",
    "please subscribe.",
    "subscribe",
    "subscribe.",
    "thank you.",
    "thank you very much.",
    "be sure to subscribe",
    "don't forget to subscribe",
}


class SparkEars:
    """Speech-to-Text using Whisper with hallucination filtering."""

    def __init__(self) -> None:
        self._model = None

    def _get_model(self) -> Any:
        if self._model is None:
            try:
                import whisper
                self._model = whisper.load_model("base")
                logger.info("Whisper model loaded")
            except ImportError:
                logger.warning("whisper not installed: pip install openai-whisper")
                return None
            except Exception as exc:
                logger.warning("Whisper load failed: %s", exc)
                return None
        return self._model

    def listen(self, duration: int = 5) -> str | None:
        """Listen for speech and return transcription."""
        model = self._get_model()
        if model is None:
            return None

        try:
            import pyaudio
            import numpy as np

            chunk = 1024
            sample_rate = 16000
            format = pyaudio.paInt16
            channels = 1

            p = pyaudio.PyAudio()
            stream = p.open(
                format=format,
                channels=channels,
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

            result = model.transcribe(audio_data, language="en")
            raw_text = result.get("text", "")

            return self._filter(raw_text)

        except ImportError:
            logger.warning("pyaudio not installed: pip install pyaudio")
            return None
        except Exception as exc:
            logger.warning("STT failed: %s", exc)
            return None

    def _filter(self, text: str) -> str | None:
        """Filter hallucinations and short transcriptions."""
        if not text:
            return None

        text = text.strip()
        normalized = text.lower().rstrip(".!? \t\n")

        if normalized in WHISPER_HALLUCINATIONS:
            logger.info("Filtered hallucination: '%s'", text)
            return None

        min_length = int(os.getenv("SPARK_SILENCE_MIN_LENGTH", "3"))
        if len(normalized) < min_length:
            logger.info("Filtered short transcription: '%s' (length %d < %d)", text, len(normalized), min_length)
            return None

        return text
