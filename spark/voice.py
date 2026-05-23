from typing import Any

from tools.voice import speak
from audio.stt import SparkEars


class SparkVoice:
    def __init__(self, config: dict[str, Any]):
        self.config = config if isinstance(config, dict) else {}
        self.ears = SparkEars()

    def listen(self) -> str:
        voice_config = self.config.get("voice", {}) if isinstance(self.config, dict) else {}
        duration = int(voice_config.get("stt_seconds", 5))
        res = self.ears.listen(duration)
        if res is None:
            return ""
        return res

    async def speak(self, text: str) -> None:
        await speak(text)

