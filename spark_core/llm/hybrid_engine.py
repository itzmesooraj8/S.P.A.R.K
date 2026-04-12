import asyncio
import json
import os
import time
from typing import Optional

import httpx

_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
_DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
_OLLAMA_POLL_SECONDS = int(os.getenv("OLLAMA_HEALTH_POLL_SECONDS", "10"))

class HybridLLM:
    """
    Local-first LLM engine backed by Ollama only.
    No external cloud API keys are required for this loop.
    """
    def __init__(self, model: str = _DEFAULT_MODEL, ollama_host: str = _DEFAULT_OLLAMA_HOST):
        self.model = (model or _DEFAULT_MODEL).strip() or _DEFAULT_MODEL
        self.host = (ollama_host or _DEFAULT_OLLAMA_HOST).rstrip("/")
        self._ollama_online = False
        self._last_health_check = 0.0
        self._poll_task: Optional[asyncio.Task] = None
        self._poll_interval_s = max(3, _OLLAMA_POLL_SECONDS)

        self._ollama_online = self._check_ollama_health_sync()
        if self._ollama_online:
            print(f"[LLM] Ollama ONLINE - {self.model} ready")
        else:
            print("[LLM] WARNING: Ollama offline at startup; background poller enabled")

    def _check_ollama_health_sync(self) -> bool:
        try:
            res = httpx.get(f"{self.host}/api/tags", timeout=2.0)
            return res.status_code == 200
        except Exception:
            return False

    async def _check_ollama_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=2.0) as client:
                r = await client.get(f"{self.host}/api/tags")
                return r.status_code == 200
        except Exception:
            return False

    async def _update_ollama_status(self, force: bool = False) -> bool:
        now = time.monotonic()
        if not force and (now - self._last_health_check) < self._poll_interval_s:
            return self._ollama_online

        online = await self._check_ollama_health()
        self._last_health_check = now
        if online != self._ollama_online:
            if online:
                print(f"[LLM] Ollama recovered - switching to local model: {self.model}")
            else:
                print("[LLM] Ollama went offline - waiting for recovery")
        self._ollama_online = online
        return self._ollama_online

    async def _poll_ollama_health_loop(self):
        while True:
            await self._update_ollama_status(force=True)
            await asyncio.sleep(self._poll_interval_s)

    def _start_health_poller(self):
        if self._poll_task and not self._poll_task.done():
            return
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            return
        self._poll_task = loop.create_task(self._poll_ollama_health_loop())

    async def is_local_available(self) -> bool:
        return await self._update_ollama_status(force=True)

    async def _stream_local(self, system_prompt: str, user_text: str):
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            "stream": True,
        }

        timeout = httpx.Timeout(connect=3.0, read=120.0, write=15.0, pool=5.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream("POST", f"{self.host}/api/chat", json=payload) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise RuntimeError(f"Ollama /api/chat failed: HTTP {response.status_code} {body[:200]!r}")

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    token = data.get("message", {}).get("content")
                    if token:
                        yield token

    async def generate(self, system_prompt: str, user_text: str):
        self._start_health_poller()

        retries = int(os.getenv("SPARK_LOCAL_RETRIES", "3"))
        last_error = None

        online = await self._update_ollama_status(force=not self._ollama_online)
        if not online:
            yield "[SPARK] Local model offline. Polling Ollama every 10s for auto-recovery."
            return

        for attempt in range(retries):
            try:
                async for token in self._stream_local(system_prompt, user_text):
                    yield token
                return
            except Exception as e:
                last_error = e
                self._ollama_online = False
                if attempt < retries - 1:
                    await self._update_ollama_status(force=True)
                    await asyncio.sleep(1)

        print(f"[LLM] Local generation failed after {retries} retries: {last_error!r}")
        yield "[SPARK] Local model is currently unavailable. Polling Ollama every 10s and will auto-recover when online."
