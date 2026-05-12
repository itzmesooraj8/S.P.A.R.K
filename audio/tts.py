from __future__ import annotations

import asyncio

from tools.voice import speak as speak_async


class SparkVoice:
    def __init__(self):
        pass

    def speak(self, text):
        try:
            asyncio.run(speak_async(text))
        except RuntimeError:
            import threading

            threading.Thread(target=lambda: asyncio.run(speak_async(text)), daemon=True).start()

    def stop(self):
        pass
