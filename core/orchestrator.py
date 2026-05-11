"""Groq-native LLM orchestrator for S.P.A.R.K."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any, Callable

from dotenv import load_dotenv
from groq import Groq

from core.memory import MemoryStore

load_dotenv()

try:
    from tools.search import web_search
except Exception:  # pragma: no cover - optional dependency guard
    try:
        from tools.web_search import web_search
    except Exception:  # pragma: no cover - optional dependency guard
        def web_search(*args, **kwargs):  # type: ignore[no-redef]
            raise ImportError("web_search tool is unavailable")

try:
    from tools.system import get_system_stats
except Exception:  # pragma: no cover - optional dependency guard
    try:
        from tools.sysmon import get_system_health as get_system_stats
    except Exception:  # pragma: no cover - optional dependency guard
        def get_system_stats(*args, **kwargs):  # type: ignore[no-redef]
            raise ImportError("get_system_stats tool is unavailable")

try:
    from tools.clipboard import get_clipboard
except Exception:  # pragma: no cover - optional dependency guard
    def get_clipboard(*args, **kwargs):  # type: ignore[no-redef]
        raise ImportError("get_clipboard tool is unavailable")

try:
    from tools.browser import open_app, open_url
except Exception:  # pragma: no cover - optional dependency guard
    def open_url(*args, **kwargs):  # type: ignore[no-redef]
        raise ImportError("open_url tool is unavailable")

    def open_app(*args, **kwargs):  # type: ignore[no-redef]
        raise ImportError("open_app tool is unavailable")

try:
    from tools.news import get_news
except Exception:  # pragma: no cover - optional dependency guard
    def get_news(*args, **kwargs):  # type: ignore[no-redef]
        raise ImportError("get_news tool is unavailable")

try:
    from tools.weather import get_weather
except Exception:  # pragma: no cover - optional dependency guard
    def get_weather(*args, **kwargs):  # type: ignore[no-redef]
        raise ImportError("get_weather tool is unavailable")

try:
    from tools.network import get_network_connections
except Exception:  # pragma: no cover - optional dependency guard
    def get_network_connections(*args, **kwargs):  # type: ignore[no-redef]
        raise ImportError("get_network_connections tool is unavailable")

try:
    from tools.voice import speak
except Exception:  # pragma: no cover - optional dependency guard
    async def speak(*args, **kwargs):  # type: ignore[no-redef]
        return "Speech unavailable."


client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
memory = MemoryStore()

SYSTEM_PROMPT = (
    "You are S.P.A.R.K — Sentient Proactive Autonomous Response Kernel. "
    "You run locally on the user's machine. Use tools when the request benefits from real data. "
    "Be direct, concise. Never hallucinate fetchable data."
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, facts, and news.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_stats",
            "description": "Get CPU, RAM, disk, GPU, and other system stats.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_clipboard",
            "description": "Read what is currently in the user's clipboard.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL directly, or a map search when query is provided.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "query": {"type": "string", "description": "Map search or location query"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get the latest news headlines for a topic.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Topic or keyword"},
                },
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a location.",
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "City or place name"},
                },
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_network_connections",
            "description": "Show active network connections and open ports.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "speak",
            "description": "Speak text aloud using local TTS.",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Text to speak"},
                },
                "required": ["text"],
            },
        },
    },
]


def _stringify_result(result: Any) -> str:
    """Convert a tool result into a string for the follow-up LLM call."""
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False)
    except Exception:
        return str(result)


def _schedule_speak(text: str) -> str:
    """Schedule local TTS without blocking the orchestrator."""
    asyncio.create_task(speak(text))
    return "Speech scheduled."


def _call_tool(tool_name: str, tool_args: dict[str, Any]) -> Any:
    """Dispatch a tool call using the provided tool name and arguments."""
    if tool_name == "speak":
        return _schedule_speak(tool_args["text"])
    return TOOL_MAP[tool_name](tool_args)


TOOL_MAP: dict[str, Callable[[dict[str, Any]], Any]] = {
    "web_search": lambda args: web_search(**args),
    "get_system_stats": lambda args: get_system_stats(),
    "get_clipboard": lambda args: get_clipboard(),
    "open_url": lambda args: open_url(**args),
    "get_news": lambda args: get_news(**args),
    "get_weather": lambda args: get_weather(**args),
    "get_network_connections": lambda args: get_network_connections(),
    "speak": lambda args: _schedule_speak(args["text"]),
}


def _chat_completion(messages: list[dict[str, Any]], allow_tools: bool = True):
    """Execute one Groq chat completion request."""
    if client is None:
        raise RuntimeError("GROQ_API_KEY is not configured")

    kwargs: dict[str, Any] = {
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": messages,
        "max_tokens": 1024,
    }
    if allow_tools:
        kwargs["tools"] = TOOLS
        kwargs["tool_choice"] = "auto"
    return client.chat.completions.create(**kwargs)


async def handle(user_input: str, session_history: list[dict[str, Any]]) -> dict[str, Any]:
    """Process one user request with memory-aware Groq tool calling."""
    try:
        memories = memory.recall(user_input, top_k=3)
    except Exception:
        memories = []

    memory_block = "\n[MEMORY]\n" + "\n".join(f"- {item}" for item in memories) if memories else ""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + memory_block},
        *session_history[-10:],
        {"role": "user", "content": user_input},
    ]

    try:
        memory.extract_and_store_facts(user_input)
    except Exception:
        pass

    if client is None:
        reply = "Groq is not configured. Set GROQ_API_KEY to enable SPARK function calling."
        try:
            memory.store(f"User: {user_input} | SPARK: {reply[:200]}")
        except Exception:
            pass
        return {"reply": reply, "tool_used": None, "tool_result": None}

    first_response = await asyncio.to_thread(_chat_completion, messages, True)
    message = first_response.choices[0].message
    tool_used = None
    tool_result: Any = None

    if getattr(message, "tool_calls", None):
        tool_call = message.tool_calls[0]
        tool_used = tool_call.function.name
        try:
            tool_args = json.loads(tool_call.function.arguments or "{}")
        except json.JSONDecodeError:
            tool_args = {}

        try:
            tool_result = await asyncio.to_thread(_call_tool, tool_used, tool_args)
        except Exception as exc:
            tool_result = f"Tool error: {exc}"

        messages.append({"role": "assistant", "content": None, "tool_calls": message.tool_calls})
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": _stringify_result(tool_result)})

        second_response = await asyncio.to_thread(_chat_completion, messages, True)
        reply = (second_response.choices[0].message.content or "").strip()
    else:
        reply = (message.content or "").strip()

    if not reply:
        reply = "I do not have a response right now."

    try:
        memory.store(f"User: {user_input} | SPARK: {reply[:200]}")
    except Exception:
        pass

    return {"reply": reply, "tool_used": tool_used, "tool_result": tool_result}
