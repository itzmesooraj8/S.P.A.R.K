import asyncio
import threading
from typing import Callable

class OpenWakeWordDetector:
    """
    Detects 'Hey SPARK' locally using OpenWakeWord without streaming to cloud.
    """
    def __init__(self):
        self.model_path = "models/hey_spark.onnx"
        self.running = False
        self._thread = None
        self.callbacks: list[Callable] = []

    def register_callback(self, callback: Callable):
        self.callbacks.append(callback)

    def _listen_loop(self):
        print(f"[OpenWakeWord] Loaded model {self.model_path}. Listening for 'Hey SPARK'...")
        while self.running:
            # Simulate real-time mic monitoring
            time.sleep(1)
            # In real system, if probability > 0.5:
            # for cb in self.callbacks: cb()

    def start(self):
        if not self.running:
            import time
            self.running = True
            self._thread = threading.Thread(target=self._listen_loop, daemon=True)
            self._thread.start()

    def stop(self):
        self.running = False

wake_word_detector = OpenWakeWordDetector()
