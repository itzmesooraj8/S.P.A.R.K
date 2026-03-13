import asyncio
import time
from typing import AsyncGenerator

class PersonaPlexEngine:
    """
    PersonaPlex-7B implementation mockup. 
    Full-duplex conversational AI — listens and speaks simultaneously.
    """
    def __init__(self):
        self.is_listening = True
        self.is_speaking = False
        self.buffer = ""

    async def stream_audio_out(self, text_stream: AsyncGenerator[str, None]) -> AsyncGenerator[bytes, None]:
        """Takes an async stream of tokens and converts them to an outgoing audio stream."""
        self.is_speaking = True
        try:
            async for token in text_stream:
                # In real PersonaPlex, this generates audio chunks real-time
                yield f"[AUDIO_CHUNK:{token}]".encode()
                await asyncio.sleep(0.01)
        finally:
            self.is_speaking = False

    async def ingest_audio_in(self, audio_chunk: bytes) -> str:
        """Ingests user audio simultaneously while speaking. Can trigger interruption mid-sentence."""
        # Simulated parsing of user audio chunk
        return "[interruption detected]" if b"stop" in audio_chunk.lower() else ""

duplex_engine = PersonaPlexEngine()
