import logging
import os
from tools.voice import listen_and_transcribe

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
    def listen(self, duration: int = 5) -> str | None:
        raw_text = listen_and_transcribe(duration)
        if not raw_text:
            return None

        text = raw_text.strip()
        normalized = text.lower().rstrip(".!? \t\n")

        # Validate against blacklist
        if normalized in WHISPER_HALLUCINATIONS or any(normalized == phrase.lower().rstrip(".!? \t\n") for phrase in WHISPER_HALLUCINATIONS):
            logger.info("Filtered out Whisper hallucination: '%s'", text)
            return None

        # Validate length against SPARK_SILENCE_MIN_LENGTH
        min_length = int(os.getenv("SPARK_SILENCE_MIN_LENGTH", "3"))
        if len(normalized) < min_length:
            logger.info("Filtered out short/silent transcription: '%s' (length %d < %d)", text, len(normalized), min_length)
            return None

        return text

