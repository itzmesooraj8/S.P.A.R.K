"""
LLM Bridge — Clean async interface to LLM backends.

Backend priority: Groq → Ollama → Deterministic fallback

Single async function: ask(prompt, system_prompt, max_tokens) -> str
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

logger = logging.getLogger("spark.llm_bridge")

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OLLAMA_API_URL = "http://localhost:11434/api/chat"


@dataclass
class TokenBudget:
    daily_limit: int = 80_000
    used: int = 0
    reset_date: str = ""
    groq_calls: int = 0
    ollama_calls: int = 0
    fallback_calls: int = 0

    def reset_if_new_day(self) -> None:
        today = time.strftime("%Y-%m-%d")
        if self.reset_date != today:
            self.used = 0
            self.reset_date = today

    def can_use_groq(self) -> bool:
        self.reset_if_new_day()
        return self.used < self.daily_limit

    def record_usage(self, tokens: int, backend: str) -> None:
        today = time.strftime("%Y-%m-%d")
        if self.reset_date != today:
            self.used = 0
            self.reset_date = today
        self.used += tokens
        if backend == "groq":
            self.groq_calls += 1
        elif backend == "ollama":
            self.ollama_calls += 1
        else:
            self.fallback_calls += 1

    def stats(self) -> dict[str, Any]:
        self.reset_if_new_day()
        return {
            "used": self.used,
            "daily_limit": self.daily_limit,
            "remaining": max(0, self.daily_limit - self.used),
            "groq_calls": self.groq_calls,
            "ollama_calls": self.ollama_calls,
            "fallback_calls": self.fallback_calls,
        }


@dataclass
class LLMError(Exception):
    message: str
    backend: str
    cause: str = ""


class LLMBridge:
    """
    Clean async interface to LLM backends.

    Usage:
        bridge = LLMBridge()
        response = await bridge.ask("What is Python?", max_tokens=100)
    """

    def __init__(self) -> None:
        self.budget = TokenBudget()
        self._ollama_models = ["gemma2:2b", "qwen2.5:0.5b"]

    async def ask(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> str:
        """Send a prompt and get a response. Tries Groq → Ollama → deterministic."""

        if self.budget.can_use_groq():
            try:
                return await self._ask_groq(prompt, system_prompt, max_tokens, temperature)
            except Exception as exc:
                logger.debug("Groq failed: %s", exc)

        try:
            return await self._ask_ollama(prompt, system_prompt, max_tokens, temperature)
        except Exception as exc:
            logger.debug("Ollama failed: %s", exc)

        return self._deterministic_fallback(prompt)

    async def _ask_groq(
        self, prompt: str, system_prompt: str, max_tokens: int, temperature: float
    ) -> str:
        api_key = os.environ.get("GROQ_API_KEY", "")
        if not api_key:
            raise LLMError(message="No GROQ_API_KEY set", backend="groq")

        model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient() as client:
            response = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=30.0,
            )
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            tokens = usage.get("total_tokens", 0)
            self.budget.record_usage(tokens, "groq")

            return content.strip()

    async def _ask_ollama(
        self, prompt: str, system_prompt: str, max_tokens: int, temperature: float
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for model in self._ollama_models:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        OLLAMA_API_URL,
                        json={
                            "model": model,
                            "messages": messages,
                            "stream": False,
                            "options": {
                                "num_predict": max_tokens,
                                "temperature": temperature,
                            },
                        },
                        timeout=60.0,
                    )
                    response.raise_for_status()
                    content = response.json().get("message", {}).get("content", "")
                    self.budget.record_usage(0, "ollama")
                    return content.strip()
            except Exception:
                continue

        raise LLMError(message="All Ollama models failed", backend="ollama")

    def _deterministic_fallback(self, prompt: str) -> str:
        self.budget.record_usage(0, "deterministic")
        prompt_lower = prompt.lower()

        if any(w in prompt_lower for w in ["what is", "define", "explain"]):
            return f"I can provide information about that, but the LLM backend is currently unavailable. Your query was: {prompt[:100]}"
        if any(w in prompt_lower for w in ["hello", "hi", "hey"]):
            return "Hello, sir. The language model is currently unavailable, but I'm still operational."
        if any(w in prompt_lower for w in ["help", "what can you do"]):
            return "I can assist with goals, actions, memory, and system status. The LLM is currently offline, but deterministic functions are available."

        return "The language model is currently unavailable. I can still perform deterministic actions like opening applications, searching files, and checking system status."

    def stats(self) -> dict[str, Any]:
        return self.budget.stats()
