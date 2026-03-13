import asyncio
import queue

class FasterWhisperStream:
    """
    Real-time continuous STT using faster-whisper.
    """
    def __init__(self):
        self.model_size = "base.en"
        self.audio_queue = queue.Queue()
        self.is_transcribing = False

    def push_audio(self, audio_bytes: bytes):
        """Websocket streams raw PCM data here."""
        self.audio_queue.put(audio_bytes)

    async def transcribe_stream(self) -> AsyncGenerator[str, None]:
        """Yields localized transcriptions as audio arrives."""
        self.is_transcribing = True
        try:
            while self.is_transcribing:
                if not self.audio_queue.empty():
                    chunk = self.audio_queue.get()
                    # simulated transcription
                    await asyncio.sleep(0.05)
                    yield "[TRANSCRIPT_CHUNK]"
                else:
                    await asyncio.sleep(0.1)
        finally:
            self.is_transcribing = False

stt_streamer = FasterWhisperStream()
