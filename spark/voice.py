from __future__ import annotations

from typing import Any

from tools.voice import listen_and_transcribe, speak


class SparkVoice:
    def __init__(self, config: dict[str, Any]):
        self.config = config if isinstance(config, dict) else {}

    def listen(self) -> str:
        voice_config = self.config.get("voice", {}) if isinstance(self.config, dict) else {}
        duration = int(voice_config.get("stt_seconds", 5))
        return listen_and_transcribe(duration)

    async def speak(self, text: str) -> None:
        await speak(text)
