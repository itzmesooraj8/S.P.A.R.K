import asyncio
import json
import os
import time
from typing import Optional

import httpx


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default

_DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
_DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
_OLLAMA_POLL_SECONDS = _int_env("OLLAMA_HEALTH_POLL_SECONDS", 10)
_MAX_INPUT_CHARS = _int_env("SPARK_MAX_INPUT_CHARS", 8000)
_MAX_SYSTEM_PROMPT_CHARS = _int_env("SPARK_MAX_SYSTEM_PROMPT_CHARS", 12000)
_MAX_TOTAL_PROMPT_CHARS = _int_env("SPARK_MAX_TOTAL_PROMPT_CHARS", 18000)
_MAX_PREDICT_TOKENS = _int_env("SPARK_OLLAMA_MAX_TOKENS", 1024)
_MEMORY_PRESSURE_THRESHOLD = _float_env("SPARK_MEMORY_PRESSURE_PCT", 92.0)

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
        self._max_input_chars = max(128, _MAX_INPUT_CHARS)
        self._max_system_prompt_chars = max(512, _MAX_SYSTEM_PROMPT_CHARS)
        self._max_total_prompt_chars = max(
            self._max_input_chars,
            _MAX_TOTAL_PROMPT_CHARS,
        )
        self._max_predict_tokens = max(64, _MAX_PREDICT_TOKENS)
        self._memory_pressure_threshold = max(75.0, _MEMORY_PRESSURE_THRESHOLD)

        self._ollama_online = self._check_ollama_health_sync()
        if self._ollama_online:
            print(f"[LLM] Ollama ONLINE - {self.model} ready")
        else:
            print("[LLM] WARNING: Ollama offline at startup; background poller enabled")

    def _within_prompt_budget(self, system_prompt: str, user_text: str) -> tuple[str, str]:
        system_text = (system_prompt or "").strip()
        user_message = (user_text or "").strip()

        if len(user_message) > self._max_input_chars:
            user_message = user_message[: self._max_input_chars]

        if len(system_text) > self._max_system_prompt_chars:
            # Keep the latest context segment when trimming long system prompts.
            system_text = system_text[-self._max_system_prompt_chars :]

        total_chars = len(system_text) + len(user_message)
        if total_chars > self._max_total_prompt_chars:
            overflow = total_chars - self._max_total_prompt_chars

            if overflow > 0 and len(system_text) > 512:
                trim_system = min(overflow, len(system_text) - 512)
                system_text = system_text[trim_system:]
                overflow -= trim_system

            if overflow > 0 and user_message:
                user_message = user_message[: max(1, len(user_message) - overflow)]

        return system_text, user_message

    def _memory_pressure_block(self) -> bool:
        try:
            import psutil

            return psutil.virtual_memory().percent >= self._memory_pressure_threshold
        except Exception:
            return False

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
        bounded_system_prompt, bounded_user_text = self._within_prompt_budget(system_prompt, user_text)
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": bounded_system_prompt},
                {"role": "user", "content": bounded_user_text},
            ],
            "stream": True,
            "options": {"num_predict": self._max_predict_tokens},
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

        if self._memory_pressure_block():
            yield (
                "[SPARK] Memory pressure is high. Generation paused to avoid OOM. "
                "Please retry after active tasks settle."
            )
            return

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
