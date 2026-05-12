from __future__ import annotations

from tools.voice import listen_and_transcribe


class SparkEars:
    def listen(self, duration: int = 5):
        return listen_and_transcribe(duration)
