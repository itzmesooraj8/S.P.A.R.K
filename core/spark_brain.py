"""S.P.A.R.K spark brain - Groq-native tool calling."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from groq import Groq

from core.memory import MemoryStore, MemoryCategory

logger = logging.getLogger(__name__)

try:
    from tools.browser import open_app, open_url
except ImportError as e:
    logger.warning(f"Failed to import browser tools: {e}")

try:
    from tools.clipboard import get_clipboard
except ImportError as e:
    logger.warning(f"Failed to import clipboard tools: {e}")

try:
    from tools.network import get_network_connections
except ImportError as e:
    logger.warning(f"Failed to import network tools: {e}")

try:
    from tools.news import get_news
except ImportError as e:
    logger.warning(f"Failed to import news tools: {e}")

try:
    from tools.search import web_search
except ImportError as e:
    logger.warning(f"Failed to import search tools: {e}")

try:
    from tools.system import get_system_stats
except ImportError as e:
    logger.warning(f"Failed to import system tools: {e}")

try:
    from tools.weather import get_weather
except ImportError as e:
    logger.warning(f"Failed to import weather tools: {e}")

try:
    from tools.screen import read_screen, read_region
except ImportError as e:
    logger.warning(f"Failed to import screen tools: {e}")

try:
    from tools.iot import control_device
except ImportError as e:
    logger.warning(f"Failed to import iot tools: {e}")

try:
    from tools.home import scene_leaving, scene_arriving, scene_good_night
except ImportError as e:
    logger.warning(f"Failed to import home tools: {e}")

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY")) if os.getenv("GROQ_API_KEY") else None
memory = MemoryStore()

SYSTEM_PROMPT = """You are S.P.A.R.K — Sentient Proactive Autonomous Response Kernel.
You run directly on the user's Windows machine. You have real tools and real
system access. You are NOT a cloud chatbot. You CAN and WILL:

- Open any application the user asks for
- Read the screen, files, clipboard
- Search the web for any information
- Control smart home devices
- Run system commands
- Do anything the user requests

CRITICAL RULES:
1. NEVER say "I can't", "I don't have the ability", "I'm just a language model"
2. If you have a tool that does the task — USE IT
3. If no tool fits — use the execute_python tool to write and run code that does it
4. Always attempt the task. Always provide a result.
5. Be concise. Confirm what you did, not what you can't do.

EXAMPLES of using execute_python to open apps on Windows:
- Open Spotify: subprocess.Popen(['explorer.exe', 'spotify:'])
- Open Telegram: subprocess.Popen(['explorer.exe', 'tg:'])  
- Open File Explorer: subprocess.Popen(['explorer.exe'])
- Open Camera: subprocess.Popen(['explorer.exe', 'microsoft.windows.camera:'])
- Open any app by name: subprocess.Popen(['cmd', '/c', 'start', '', 'AppName'])
- Open Brave/Chrome: subprocess.Popen(['cmd', '/c', 'start', '', 'brave'])
Always import subprocess at the top of the code block.
"""

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
            "parameters": {
                "type": "object", 
                "properties": {},
                "required": []
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_clipboard",
            "description": "Read what is currently in the user's clipboard",
            "parameters": {
                "type": "object", 
                "properties": {},
                "required": []
            },
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
                "required": []
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_python",
            "description": "Execute any Python code on the user's machine to complete a task. Use this when no specific tool exists. Can open apps, move files, read data, automate anything on Windows. Write complete, runnable Python code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Complete Python code to execute. Must be self-contained and runnable."
                    },
                    "description": {
                        "type": "string",
                        "description": "One sentence: what this code does"
                    }
                },
                "required": ["code", "description"]
            }
        }
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
            "parameters": {
                "type": "object", 
                "properties": {},
                "required": []
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_screen",
            "description": "Read all text visible on the user's screen right now using OCR. Use when user says 'read my screen', 'what's on my screen', 'read this for me'",
            "parameters": {
                "type": "object", 
                "properties": {},
                "required": []
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_region",
            "description": "Read text from a specific region of the screen by pixel coordinates",
            "parameters": {
                "type": "object",
                "properties": {
                    "x1": {"type": "integer"},
                    "y1": {"type": "integer"},
                    "x2": {"type": "integer"},
                    "y2": {"type": "integer"}
                },
                "required": ["x1", "y1", "x2", "y2"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "control_device",
            "description": "Control a smart home device via MQTT. Devices: fan, light, bedroom_light, ac. Actions: on, off",
            "parameters": {
                "type": "object",
                "properties": {
                    "device": {"type": "string"},
                    "action": {"type": "string"}
                },
                "required": ["device", "action"]
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scene_leaving",
            "description": "Trigger the scene when leaving the house",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scene_arriving",
            "description": "Trigger the scene when arriving at the house",
            "parameters": {
                "type": "object",
                "properties": {
                    "eta_minutes": {"type": "integer"}
                },
                "required": []
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "scene_good_night",
            "description": "Trigger the good night scene for sleep",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            },
        },
    }
]


try:
    json.dumps(TOOLS)
except Exception as e:
    raise ValueError(f"SPARK: TOOLS list is not valid JSON: {e}")

import subprocess, sys, tempfile

def _execute_python(code: str, description: str = "") -> str:
    """
    Execute Python code in a subprocess. Returns stdout/stderr.
    This is how SPARK does ANYTHING it doesn't have a specific tool for.
    """
    try:
        # Write code to temp file
        tmp = tempfile.mktemp(suffix=".py")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(code)
        
        result = subprocess.run(
            [sys.executable, tmp],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=os.path.expanduser("~"),
        )
        os.unlink(tmp)
        
        output = result.stdout.strip()
        errors = result.stderr.strip()
        
        if result.returncode == 0:
            return output if output else f"Done: {description}"
        else:
            # Try to self-correct: return error so LLM can retry with fixed code
            return f"Error (returncode={result.returncode}): {errors}"
    except subprocess.TimeoutExpired:
        return "Timeout: code took too long (>15s)"
    except Exception as e:
        return f"Execution error: {e}"

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
    if tool_name == "execute_python":
        return _execute_python(tool_args["code"], tool_args.get("description", ""))
    if tool_name == "get_news":
        return get_news(tool_args["topic"])
    if tool_name == "get_weather":
        return get_weather(tool_args["location"])
    if tool_name == "get_network_connections":
        return get_network_connections()
    if tool_name == "read_screen":
        return read_screen()
    if tool_name == "read_region":
        return read_region(tool_args["x1"], tool_args["y1"], tool_args["x2"], tool_args["y2"])
    if tool_name == "control_device":
        return control_device(tool_args["device"], tool_args["action"])
    if tool_name == "scene_leaving":
        return asyncio.create_task(scene_leaving()) or "Leaving scene triggered."
    if tool_name == "scene_arriving":
        return asyncio.create_task(scene_arriving(tool_args.get("eta_minutes", 10))) or "Arrival scene triggered."
    if tool_name == "scene_good_night":
        return asyncio.create_task(scene_good_night()) or "Good night scene triggered."
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

    # Speak every reply out loud
    try:
        from tools.voice import speak
        asyncio.create_task(speak(reply))
    except RuntimeError:
        # No running event loop (e.g. called from sync context)
        import threading
        from tools.voice import speak
        threading.Thread(
            target=lambda: asyncio.run(speak(reply)),
            daemon=True
        ).start()
    except Exception as e:
        logger.error(f"TTS Error: {e}")

    return {"reply": reply, "tool_used": tool_used, "tool_result": tool_result}