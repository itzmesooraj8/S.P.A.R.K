from __future__ import annotations

import asyncio
import time
import subprocess
import numpy as np

class FlowCoordinator:
    def __init__(self):
        self.input_queue: asyncio.Queue[str] = asyncio.Queue()
        self.execution_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.active_tasks: list[asyncio.Task] = []

    async def start(self):
        self.active_tasks.append(asyncio.create_task(self._process_input_tokens()))
        self.active_tasks.append(asyncio.create_task(self._execute_tool_pipelines()))

    async def inject_user_input(self, text: str):
        await self.input_queue.put(text)

    async def _process_input_tokens(self):
        while True:
            text = await self.input_queue.get()
            payload = {"action": "route_intent", "text": text, "timestamp": time.time()}
            await self.execution_queue.put(payload)
            self.input_queue.task_done()

    async def _execute_tool_pipelines(self):
        while True:
            task_payload = await self.execution_queue.get()
            # Asynchronously processes task execution
            self.execution_queue.task_done()

class AudioInterruptController:
    def __init__(self, tts_player_process: subprocess.Popen | None = None):
        self.tts_process = tts_player_process
        self.interrupt_event = asyncio.Event()

    def detect_barge_in(self, input_chunk: np.ndarray, threshold: float = 350.0) -> bool:
        """Determines if user vocal signal breaks outgoing audio stream."""
        if len(input_chunk) == 0:
            return False
        rms = np.sqrt(np.mean(input_chunk.astype(np.float32)**2))
        if rms > threshold:
            self.terminate_active_speech()
            return True
        return False

    def terminate_active_speech(self):
        if self.tts_process and self.tts_process.poll() is None:
            try:
                self.tts_process.kill()
            except Exception:
                pass
            self.tts_process = None
            self.interrupt_event.set()
