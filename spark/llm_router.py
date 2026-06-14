"""
LLM Intent Router — Classifies user intent using LLM.

Returns one of exactly 5 strings:
"goal_creation" | "action_execution" | "memory_query" | "status_check" | "conversation"

Backend priority: Groq → Ollama → Deterministic fallback
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx

logger = logging.getLogger("spark.llm_router")

INTENTS = ("goal_creation", "action_execution", "memory_query", "status_check", "conversation")

SYSTEM_PROMPT = """You are an intent classifier. Given a user message, classify it into exactly ONE of these categories:

- goal_creation: user wants to create a goal, plan, task, or achieve something
- action_execution: user wants to open, search, run, execute, or use a tool
- memory_query: user wants to remember, recall, or look up past information
- status_check: user wants to see status, dashboard, health, or system info
- conversation: anything else — greetings, questions, opinions, general chat

Return ONLY the intent label. No explanation. No punctuation. Just the label."""

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
OLLAMA_API_URL = "http://localhost:11434/api/chat"


async def classify_intent(message: str) -> str:
    """Classify user intent. Returns one of the 5 intent labels."""
    if not message or not message.strip():
        return "conversation"

    try:
        result = await _classify_groq(message)
        if result:
            return result
    except Exception as exc:
        logger.debug("Groq classification failed: %s", exc)

    try:
        result = await _classify_ollama(message)
        if result:
            return result
    except Exception as exc:
        logger.debug("Ollama classification failed: %s", exc)

    result = _classify_deterministic(message)
    logger.info("Deterministic fallback: '%s' -> %s", message[:50], result)
    return result


async def _classify_groq(message: str) -> str | None:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None

    model = os.environ.get("GROQ_MODEL", "llama-3.1-8b-instant")

    async with httpx.AsyncClient() as client:
        response = await client.post(
            GROQ_API_URL,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": message},
                ],
                "max_tokens": 20,
                "temperature": 0.0,
            },
            timeout=10.0,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"].strip().lower()
        return _validate_intent(content)


async def _classify_ollama(message: str) -> str | None:
    models = ["gemma2:2b", "qwen2.5:0.5b"]

    for model in models:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    OLLAMA_API_URL,
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {"role": "user", "content": message},
                        ],
                        "stream": False,
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                content = response.json().get("message", {}).get("content", "").strip().lower()
                result = _validate_intent(content)
                if result:
                    return result
        except Exception:
            continue

    return None


def _classify_deterministic(message: str) -> str:
    message_lower = message.lower().strip()
    words = set(re.findall(r'\b\w+\b', message_lower))

    conversation_keywords = ["hello", "hi ", "hey ", "how are", "what's up", "good morning", "good evening", "thanks", "thank you", "please", "help me", "can you", "tell me", "explain", "describe", "who are you", "what can you do"]

    for keyword in conversation_keywords:
        keyword_words = set(re.findall(r'\b\w+\b', keyword))
        if keyword_words.issubset(words):
            return "conversation"

    memory_keywords = ["remember", "recall", "memory", "what did i say", "what did i", "last time", "previously", "before", "what is my", "what's my", "my name", "my favorite", "what do i"]
    for keyword in memory_keywords:
        keyword_words = set(re.findall(r'\b\w+\b', keyword))
        if keyword_words.issubset(words):
            return "memory_query"

    goal_keywords = ["goal", "plan", "task", "achieve", "build", "create", "make", "develop", "implement"]
    for keyword in goal_keywords:
        if keyword in words:
            return "goal_creation"

    action_keywords = ["open", "search", "run", "execute", "launch", "start", "find", "look up", "browse", "navigate", "type", "click", "send"]
    for keyword in action_keywords:
        if keyword in words:
            return "action_execution"

    news_keywords = ["news", "headline", "current event", "what's happening", "india news", "world news", "technology news"]
    for keyword in news_keywords:
        keyword_words = set(re.findall(r'\b\w+\b', keyword))
        if keyword_words.issubset(words) or keyword in message_lower:
            return "conversation"

    status_keywords = ["show dashboard", "show status", "system health", "system status", "show metrics", "dashboard"]
    for keyword in status_keywords:
        keyword_words = set(re.findall(r'\b\w+\b', keyword))
        if keyword_words.issubset(words):
            return "status_check"

    return "conversation"


def _validate_intent(raw: str) -> str | None:
    cleaned = raw.strip().lower().replace(".", "").replace("'", "").replace('"', "")
    if cleaned in INTENTS:
        return cleaned
    for intent in INTENTS:
        if intent in cleaned:
            return intent
    return None
