"""S.P.A.R.K spark brain - Groq-native tool calling."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import httpx
import json
import logging
import os
import psutil
import subprocess
import sys
import tempfile
import time
from typing import Any

from dotenv import load_dotenv
from groq import Groq
from core.generated_tools import load_generated_tool_specs, run_generated_tool
from config import LLM_HOST, LLM_MODEL
from core.persona import build_system_prompt

from core.memory import MemoryStore, MemoryCategory
from core.mcp_manager import MCPManager
from core.planner import spark_plan_and_execute

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

_groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
client = Groq(api_key=_groq_api_key) if _groq_api_key else None
memory = MemoryStore()
mcp_manager = MCPManager()

SYSTEM_PROMPT = """You are S.P.A.R.K — Sentient Proactive Autonomous Response Kernel.
You run on the user's Windows machine with real system access.

ABSOLUTE RULES — NEVER BREAK THESE:
1. NEVER confirm an action unless the tool returned SUCCESS or a positive result
2. If the tool returns FAILED or LAUNCH_FAILED, tell the user honestly and try a different method
3. NEVER say "I opened X" if execute_python returned LAUNCH_FAILED
4. NEVER say "I cannot" — instead, try a different approach

WHEN OPENING APPS, try in this order:
1. subprocess.Popen(['cmd', '/c', 'start', '', 'AppName'])
2. subprocess.Popen(['powershell', '-Command', 'Start-Process AppName'])
3. Use winreg or filesystem search to find the app install path, then launch it directly
4. subprocess.Popen(['explorer.exe', 'URI:']) for URI-based apps

open_app_smart example:
User: open Discord
Assistant: I will try verified launch methods and only confirm success if the process is actually visible.
open_app_smart("Discord") -> SUCCESS: Launched. New process: Discord.exe
Assistant: Discord is open.

User: open Discord
Assistant: I will try verified launch methods and only confirm success if the process is actually visible.
open_app_smart("Discord") -> LAUNCH_FAILED: Code ran without errors but no new process appeared.
Assistant: Discord did not open. I will try a different method.

FAILURE RECOVERY:
- If one method fails, automatically try the next method
- Tell the user what happened only after you have a SUCCESS result
- If all methods fail, tell the user honestly that the app could not be opened

Be concise. Speak results, not process.
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
            "description": "Execute Python code on the user's machine with verification-first results. Use this when no specific tool exists. When opening apps, the code must verify that a new process actually appeared before returning success.",
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
            "name": "spark_plan_and_execute",
            "description": "Break a complex goal into up to 5 steps, execute them safely, and return a concise progress report plus result.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "The user goal to plan and execute"}
                },
                "required": ["goal"]
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


def _execute_python(code: str, description: str = "") -> str:
    """
    Execute Python code. Returns VERIFIED result — never lies.
    If the task involves launching a process, verifies it is running.
    """
    before_procs = {p.info.get("name", "").lower() for p in psutil.process_iter(["name"])}

    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as tmp_file:
            tmp_file.write(code)
            tmp_path = tmp_file.name

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=os.path.expanduser("~"),
        )

        try:
            os.unlink(tmp_path)
        except Exception:
            pass

        output = result.stdout.strip()
        errors = result.stderr.strip()

        time.sleep(0.8)
        after_procs = {p.info.get("name", "").lower() for p in psutil.process_iter(["name"])}
        new_procs = sorted(name for name in after_procs - before_procs if name)

        if result.returncode != 0:
            return f"FAILED: {errors}\nTell the user it failed and try a different approach."

        app_keywords = ["popen", "startfile", "start", "explorer", "start-process"]
        if any(keyword in code.lower() for keyword in app_keywords):
            if new_procs:
                proc_name = new_procs[0]
                return f"SUCCESS: Launched. New process: {proc_name}\n{output}".strip()
            return f"LAUNCH_FAILED: Code ran without errors but no new process appeared. Output: {output or 'none'}. Try a different launch method."

        return output if output else f"Done: {description}"

    except subprocess.TimeoutExpired:
        return "TIMEOUT: Code took longer than 15 seconds."
    except Exception as e:
        return f"ERROR: {e}"

def _stringify_result(result: Any) -> str:
    if isinstance(result, str):
        return result
    try:
        return json.dumps(result, ensure_ascii=False)
    except Exception:
        return str(result)


def _offline_reply(user_input: str) -> str:
    normalized = user_input.strip().lower()
    greetings = {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"}
    if normalized in greetings:
        return "Hello. Groq is unavailable, but I am still online locally."
    return "I am having trouble reaching the language model right now, but I am still running locally."


async def _local_chat_completion(messages: list[dict[str, Any]]) -> str:
    try:
        async with httpx.AsyncClient(timeout=180.0) as http_client:
            response = await http_client.post(
                f"{LLM_HOST}/api/chat",
                json={"model": LLM_MODEL, "messages": messages, "stream": False},
            )
            response.raise_for_status()
            message = response.json().get("message", {})
            return str(message.get("content", "")).strip()
    except Exception as exc:
        logger.warning("Local LLM fallback failed: %s", exc)
        return ""


def _chat_completion(messages: list[dict[str, Any]], allow_tools: bool = True, tools: list[dict[str, Any]] | None = None):
    kwargs: dict[str, Any] = {
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "messages": messages,
        "max_tokens": 1024,
    }
    if allow_tools:
        kwargs["tools"] = tools or TOOLS
        kwargs["tool_choice"] = "auto"
    return client.chat.completions.create(**kwargs)


async def _get_dynamic_tools() -> list[dict[str, Any]]:
    try:
        mcp_tools = await mcp_manager.list_tool_specs()
    except Exception as exc:
        logger.info("MCP tool refresh skipped: %s", exc)
        mcp_tools = []
    return TOOLS + load_generated_tool_specs() + mcp_tools


async def _run_planner(goal: str, stream_sink=None) -> dict[str, Any]:
    dynamic_tools = await _get_dynamic_tools()

    def _sync_llm(prompt: str) -> str:
        response = _chat_completion(
            [
                {"role": "system", "content": "You are SPARK's planning engine. Return only JSON."},
                {"role": "user", "content": prompt},
            ],
            allow_tools=False,
        )
        return (response.choices[0].message.content or "").strip()

    async def _tool_executor(step_name: str, step_arg: str) -> str:
        payload: dict[str, Any]
        if step_name == "web_search":
            payload = {"query": step_arg}
        elif step_name == "get_weather":
            payload = {"location": step_arg}
        elif step_name == "get_news":
            payload = {"topic": step_arg}
        elif step_name == "execute_python":
            payload = {"code": step_arg, "description": "planned execution"}
        elif step_name == "spark_plan_and_execute":
            payload = {"goal": step_arg}
        else:
            payload = {"value": step_arg}
        result = await _call_tool(step_name, payload)
        return _stringify_result(result)

    return await spark_plan_and_execute(
        goal,
        _sync_llm,
        _tool_executor,
        [tool["function"]["name"] for tool in dynamic_tools],
        stream_sink=stream_sink,
    )


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
    if tool_name == "spark_plan_and_execute":
        return await _run_planner(tool_args["goal"])
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
    try:
        return run_generated_tool(tool_name, tool_args)
    except KeyError:
        pass
    if await mcp_manager.has_tool(tool_name):
        return await mcp_manager.call_tool(tool_name, tool_args)
    raise KeyError(f"Unknown tool: {tool_name}")


async def handle(user_input: str, session_history: list[dict[str, Any]], stream_sink=None, cancel_event=None) -> dict[str, Any]:
    try:
        memory.extract_and_store_facts(user_input)
        facts = memory.recall(user_input, top_k=3, category=MemoryCategory.FACT)
        recent = memory.recall(user_input, top_k=3, category=MemoryCategory.CONVERSATION)
    except Exception as exc:
        logger.warning("Memory context unavailable; continuing without it: %s", exc)
        facts = []
        recent = []

    memories = facts + recent
    
    memory_ctx = ("\n[MEMORY]\n" + "\n".join(f"- {m}" for m in memories)) if memories else ""

    messages = [
        {"role": "system", "content": build_system_prompt(memory_ctx, prompt_addendum=SYSTEM_PROMPT)},
        *session_history[-10:],
        {"role": "user", "content": user_input},
    ]

    if stream_sink:
        stream_sink("status", {"state": "thinking"})

    if client is None:
        reply = await _local_chat_completion(messages) or _offline_reply(user_input)
        memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
        return {"reply": reply, "tool_used": None, "tool_result": None}

    try:
        tool_specs = await _get_dynamic_tools()
        response = _chat_completion(messages, allow_tools=True, tools=tool_specs)
    except Exception as exc:
        logger.warning("Tool-enabled chat failed; retrying without tools: %s", exc)
        try:
            response = _chat_completion(messages, allow_tools=False)
        except Exception as retry_exc:
            logger.error("Plain Groq retry failed: %s", retry_exc, exc_info=True)
            reply = await _local_chat_completion(messages) or _offline_reply(user_input)
            memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
            if stream_sink:
                stream_sink("response_done", {"content": reply})
            return {"reply": reply, "tool_used": None, "tool_result": None}

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

        try:
            final = client.chat.completions.create(
                model=os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
                messages=messages,
                max_tokens=1024,
            )
            reply = (final.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning("Final tool-followup completion failed; using plain assistant response: %s", exc)
            fallback = _chat_completion(messages, allow_tools=False)
            reply = (fallback.choices[0].message.content or "").strip()
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