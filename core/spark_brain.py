"""S.P.A.R.K spark brain - Groq-native tool calling."""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from core.memory import MemoryStore
from tools.browser import open_app, open_url
from tools.clipboard import get_clipboard
from tools.network import get_network_connections
from tools.news import get_news
from tools.search import web_search
from tools.system import get_system_stats
from tools.weather import get_weather
from tools.screen import read_screen

from core.memory import MemoryStore, MemoryCategory

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
memory = MemoryStore()

SYSTEM_PROMPT = """You are S.P.A.R.K — Sentient Proactive Autonomous Response Kernel.
You are a local personal AI running on the user's machine.
Use tools when the request clearly benefits from real data.
Be direct and concise. Never hallucinate data you can fetch."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, facts",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string", "description": "Search query"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_stats",
            "description": "Get CPU, RAM, disk, GPU stats of the user's computer",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_clipboard",
            "description": "Read what is currently in the user's clipboard",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_url",
            "description": "Open a URL, map, or application in the browser",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "query": {"type": "string", "description": "For maps: location to show"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "open_app",
            "description": "Open an installed application",
            "parameters": {
                "type": "object",
                "properties": {"app_name": {"type": "string"}},
                "required": ["app_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_news",
            "description": "Get latest news headlines on a topic",
            "parameters": {
                "type": "object",
                "properties": {"topic": {"type": "string", "description": "News topic or keyword"}},
                "required": ["topic"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather and forecast",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string", "description": "City name"}},
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_network_connections",
            "description": "Show active network connections and open ports for security monitoring",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_screen",
            "description": "Read the text visible on the user's screen right now using OCR. Use when user asks 'what's on my screen', 'read this for me', 'what does it say', or wants SPARK to see something.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
]


def _stringify_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False)
    except Exception:
        return str(result)


def _chat_completion(messages: list[dict[str, Any]], allow_tools: bool = True):
    kwargs: dict[str, Any] = {
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": messages,
        "max_tokens": 1024,
    }
    if allow_tools:
        kwargs["tools"] = TOOLS
        kwargs["tool_choice"] = "auto"
    return client.chat.completions.create(**kwargs)


async def _call_tool(tool_name: str, tool_args: dict[str, Any]) -> Any:
    if tool_name == "web_search":
        return web_search(tool_args["query"])
    if tool_name == "get_system_stats":
        return get_system_stats()
    if tool_name == "get_clipboard":
        return get_clipboard()
    if tool_name == "open_url":
        return open_url(tool_args.get("url", ""), tool_args.get("query", ""))
    if tool_name == "open_app":
        return open_app(tool_args["app_name"])
    if tool_name == "get_news":
        return get_news(tool_args["topic"])
    if tool_name == "get_weather":
        return get_weather(tool_args["location"])
    if tool_name == "get_network_connections":
        return get_network_connections()
    if tool_name == "read_screen":
        return read_screen()
    raise KeyError(f"Unknown tool: {tool_name}")


async def handle(user_input: str, session_history: list[dict[str, Any]], stream_sink=None, cancel_event=None) -> dict[str, Any]:
    memory.extract_and_store_facts(user_input)
    
    facts = memory.recall(user_input, top_k=3, category=MemoryCategory.FACT)
    recent = memory.recall(user_input, top_k=3, category=MemoryCategory.CONVERSATION)
    memories = facts + recent
    
    memory_ctx = ("\n[MEMORY]\n" + "\n".join(f"- {m}" for m in memories)) if memories else ""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + memory_ctx},
        *session_history[-10:],
        {"role": "user", "content": user_input},
    ]

    if stream_sink:
        stream_sink("status", {"state": "thinking"})

    if client is None:
        reply = "Groq is not configured. Set GROQ_API_KEY to enable Spark Brain."
        memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
        return {"reply": reply, "tool_used": None, "tool_result": None}

    try:
        response = _chat_completion(messages, allow_tools=True)
    except Exception as exc:
        message = str(exc)
        if "tool_use_failed" in message or "Failed to call a function" in message:
            response = _chat_completion(messages, allow_tools=False)
        else:
            raise

    msg = response.choices[0].message
    tool_used = None
    tool_result = None

    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        tool_used = tool_call.function.name
        tool_args = json.loads(tool_call.function.arguments or "{}")

        if stream_sink:
            stream_sink("tool_execute", {"tool": tool_used, "arguments": tool_args})

        try:
            tool_result = await _call_tool(tool_used, tool_args)
        except Exception as exc:
            tool_result = f"Tool error: {exc}"

        if stream_sink:
            stream_sink("tool_result", {"tool": tool_used, "status": "completed", "output": tool_result})

        messages.append({"role": "assistant", "content": None, "tool_calls": msg.tool_calls})
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": _stringify_result(tool_result)})

        final = client.chat.completions.create(
            model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
            messages=messages,
            max_tokens=1024,
        )
        reply = (final.choices[0].message.content or "").strip()
    else:
        reply = (msg.content or "").strip()

    if not reply:
        reply = "I do not have a response right now."

    memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)

    if stream_sink:
        stream_sink("response_done", {"content": reply})

    return {"reply": reply, "tool_used": tool_used, "tool_result": tool_result}