"""S.P.A.R.K spark brain - Groq-native tool calling."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import httpx
import json
import logging
import os
import psutil
import re
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote_plus
from typing import Any

from dotenv import load_dotenv
from groq import Groq
from core.generated_tools import load_generated_tool_specs, run_generated_tool
from config import LLM_HOST, LLM_MODEL
from core.persona import build_system_prompt
from core.tools import SparkTools
from spark.token_counter import TokenCounter

from core.memory import MemoryStore, MemoryCategory
from core.mcp_manager import MCPManager
from core.planner import spark_plan_and_execute

logger = logging.getLogger(__name__)
spark_tools = SparkTools()

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

# Wrap imported tool functions with action guard wrappers when available
try:
    from security.action_guard import guard_tool_function
except Exception:
    guard_tool_function = None

if guard_tool_function:
    try:
        open_app = guard_tool_function("open_app", open_app)
    except Exception:
        pass
    try:
        open_url = guard_tool_function("open_url", open_url)
    except Exception:
        pass
    try:
        web_search = guard_tool_function("web_search", web_search)
    except Exception:
        pass
    try:
        get_system_stats = guard_tool_function("get_system_stats", get_system_stats)
    except Exception:
        pass
    try:
        control_device = guard_tool_function("control_device", control_device)
    except Exception:
        pass

try:
    from tools.home import scene_leaving, scene_arriving, scene_good_night
except ImportError as e:
    logger.warning(f"Failed to import home tools: {e}")

load_dotenv()

_groq_api_key = os.getenv("GROQ_API_KEY", "").strip()
client = Groq(api_key=_groq_api_key) if _groq_api_key else None
memory = MemoryStore()
mcp_manager = MCPManager()
token_counter = TokenCounter()
_groq_cooldown_until = 0.0
_ollama_last_probe = 0.0

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
            "name": "get_time",
            "description": "Get the current date and time",
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
            "name": "open_app",
            "description": "Open a desktop application by name",
            "parameters": {
                "type": "object",
                "properties": {
                    "app": {"type": "string", "description": "Application name"}
                },
                "required": ["app"]
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


def _extract_tool_request(content: str, allowed_tools: set[str]) -> tuple[str, dict[str, Any]] | None:
    text = (content or "").strip()
    if not text:
        return None

    try:
        payload = json.loads(text)
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None

    tool_name = str(payload.get("tool") or payload.get("name") or payload.get("function") or "").strip()
    if not tool_name or tool_name not in allowed_tools:
        return None

    tool_args: dict[str, Any] | Any = payload.get("arguments")
    if tool_args is None:
        tool_args = payload.get("arg")
    if tool_args is None:
        tool_args = payload.get("value")

    if isinstance(tool_args, str):
        default_key = "query"
        if tool_name == "get_weather":
            default_key = "location"
        elif tool_name == "get_news":
            default_key = "topic"
        elif tool_name == "open_url":
            default_key = "url"
        elif tool_name == "execute_python":
            default_key = "code"
        tool_args = {default_key: tool_args}
    elif not isinstance(tool_args, dict):
        tool_args = {}

    if tool_name == "get_weather":
        tool_args.setdefault("location", str(payload.get("location") or payload.get("arg") or payload.get("value") or "current location"))
    elif tool_name == "get_news":
        tool_args.setdefault("topic", str(payload.get("topic") or payload.get("arg") or payload.get("value") or "current events"))
    elif tool_name == "web_search":
        tool_args.setdefault("query", str(payload.get("query") or payload.get("arg") or payload.get("value") or text))

    return tool_name, tool_args


def _normalize_tool_name(name: str) -> str:
    normalized = (name or "").strip()
    aliases = {
        "open_website": "open_url",
        "open_application": "open_app",
        "open_app_smart": "open_app",
    }
    return aliases.get(normalized, normalized)


def _extract_failed_generation(exc: Exception, allowed_tools: set[str]) -> tuple[str, dict[str, Any]] | None:
    text = str(exc)
    marker = "failed_generation"
    if marker not in text:
        return None

    match = re.search(r"<function=([^>]+)></function>", text)
    if not match:
        return None

    raw = match.group(1).strip()
    name_match = re.match(r"([a-zA-Z_][a-zA-Z0-9_]*)", raw)
    if not name_match:
        return None

    tool_name = _normalize_tool_name(name_match.group(1))
    if tool_name not in allowed_tools:
        return None

    rest = raw[len(name_match.group(1)):].strip()
    if not rest:
        return tool_name, {}

    if rest.startswith("(") and rest.endswith(")"):
        inner = rest[1:-1].strip().strip('"\'')
        if tool_name == "open_app":
            return tool_name, {"app": inner}
        if tool_name == "open_url":
            return tool_name, {"url": inner}
        return tool_name, {"value": inner}

    try:
        parsed = json.loads(rest)
    except Exception:
        return None

    if isinstance(parsed, list) and parsed and isinstance(parsed[0], dict):
        parsed = parsed[0]
    if not isinstance(parsed, dict):
        return None

    return tool_name, parsed


def _apply_rate_limit_cooldown(error_text: str) -> None:
    global _groq_cooldown_until
    if "rate_limit" not in error_text and "429" not in error_text:
        return

    wait_seconds = int(os.getenv("SPARK_GROQ_COOLDOWN_SECONDS", "480"))
    wait_match = re.search(r"try again in\s+([0-9]+)m([0-9]+(?:\.[0-9]+)?)s", error_text)
    if wait_match:
        minutes = int(wait_match.group(1))
        seconds = float(wait_match.group(2))
        wait_seconds = max(wait_seconds, int(minutes * 60 + seconds))

    _groq_cooldown_until = max(_groq_cooldown_until, time.time() + wait_seconds)


def _offline_reply(user_input: str) -> str:
    normalized = user_input.strip().lower()
    greetings = {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"}
    if normalized in greetings:
        return "Hello. Groq is unavailable, but I am still online locally."
    return "I am having trouble reaching the language model right now, but I am still running locally."


def _local_cli_completion(prompt: str, messages: list[dict[str, Any]] | None = None) -> str:
    """Run local Ollama model via CLI, including system prompt context if available.
    
    Args:
        prompt: The user prompt/query
        messages: Optional full message list with system prompt (for tool-forcing)
    """
    try:
        # Build context prompt that includes system instructions if messages provided
        if messages:
            system_msgs = [m.get("content", "") for m in messages if m.get("role") == "system"]
            if system_msgs:
                # Include system prompt to preserve tool-forcing instructions
                full_prompt = f"{system_msgs[0]}\n\n{prompt}"
            else:
                full_prompt = prompt
        else:
            full_prompt = prompt
        
        timeout = float(os.getenv("SPARK_OLLAMA_CLI_TIMEOUT_SECONDS", "60"))
        result = subprocess.run(
            ["ollama", "run", LLM_MODEL, full_prompt],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=timeout,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            logger.debug(f"Ollama CLI returned code {result.returncode}: {result.stderr}")
            return ""
        return (result.stdout or "").strip()
    except subprocess.TimeoutExpired:
        logger.warning(f"Ollama CLI timeout after {timeout}s")
        return ""
    except Exception as e:
        logger.debug(f"Ollama CLI error: {e}")
        return ""


def _ensure_local_ollama(force_start: bool = False) -> None:
    global _ollama_last_probe
    now = time.time()
    if not force_start and now - _ollama_last_probe < 5.0:
        return
    _ollama_last_probe = now

    try:
        from urllib.parse import urlparse

        parsed = urlparse(LLM_HOST)
        if parsed.hostname and parsed.port:
            import socket

            with socket.create_connection((parsed.hostname, parsed.port), timeout=0.5):
                return
    except Exception:
        pass

    try:
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        time.sleep(0.4)
    except Exception:
        return


async def _local_chat_completion(messages: list[dict[str, Any]]) -> str:
    """Local model completion with CLI fallback.
    
    When Groq is in cooldown, skip HTTP and go straight to CLI to save time.
    This ensures tool-forcing system prompt is passed to the local model.
    """
    try:
        # If Groq is in cooldown, skip HTTP and go directly to CLI
        if time.time() < _groq_cooldown_until:
            logger.debug("Groq in cooldown; skipping HTTP and using CLI directly")
            prompt = "\n".join(str(m.get("content", "") or "") for m in messages if m.get("content"))
            return _local_cli_completion(prompt, messages=messages)
        
        # Otherwise try HTTP with timeout
        _ensure_local_ollama()
        async with httpx.AsyncClient(timeout=30.0) as http_client:
            response = await http_client.post(
                f"{LLM_HOST}/api/chat",
                json={"model": LLM_MODEL, "messages": messages, "stream": False},
            )
            if response.status_code == 404:
                _ensure_local_ollama(force_start=True)
                response = await http_client.post(
                    f"{LLM_HOST}/api/chat",
                    json={"model": LLM_MODEL, "messages": messages, "stream": False},
                )
            if response.status_code == 404:
                prompt = "\n".join(str(m.get("content", "") or "") for m in messages if m.get("content"))
                response = await http_client.post(
                    f"{LLM_HOST}/api/generate",
                    json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
                )
            response.raise_for_status()
            payload = response.json()
            if isinstance(payload, dict) and "response" in payload:
                return str(payload.get("response", "") or "").strip()
            message = payload.get("message", {}) if isinstance(payload, dict) else {}
            return str(message.get("content", "")).strip()
    except Exception as exc:
        logger.warning("Local LLM HTTP fallback failed: %s", exc)
        prompt = "\n".join(str(m.get("content", "") or "") for m in messages if m.get("content"))
        return _local_cli_completion(prompt, messages=messages)


def _chat_completion(messages: list[dict[str, Any]], allow_tools: bool = True, tools: list[dict[str, Any]] | None = None):
    # Check if daily Groq token limit reached; skip Groq if so
    if token_counter.should_skip_groq():
        raise RuntimeError("Daily Groq token limit reached; switching to Ollama-only mode")
    
    if time.time() < _groq_cooldown_until:
        raise RuntimeError("Groq is cooling down after rate limiting")

    groq_model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    
    kwargs: dict[str, Any] = {
        "model": groq_model,
        "messages": messages,
        "max_tokens": 1024,
    }
    if allow_tools:
        kwargs["tools"] = tools or TOOLS
        kwargs["tool_choice"] = "auto"
    try:
        response = client.chat.completions.create(**kwargs)
        
        # Log token usage after successful call
        try:
            if hasattr(response, 'usage'):
                tokens_used = response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else 0
                token_counter.log_usage(tokens_used, model=groq_model)
                remaining = token_counter.get_remaining_budget()
                if remaining < 5000:
                    logger.warning(f"Groq token budget low: {remaining} tokens remaining")
        except Exception as e:
            logger.debug(f"Failed to log token usage: {e}")
        
        return response
    except Exception as exc:
        _apply_rate_limit_cooldown(str(exc))
        raise


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
    tool_name = _normalize_tool_name(tool_name)

    if tool_name == "web_search":
        return web_search(tool_args["query"])
    if tool_name == "get_time":
        return spark_tools.get_time()
    if tool_name == "get_system_stats":
        return get_system_stats()
    if tool_name == "get_clipboard":
        return get_clipboard()
    if tool_name == "open_url":
        return open_url(tool_args.get("url", ""), tool_args.get("query", ""))
    if tool_name == "open_app":
        app_name = str(tool_args.get("app") or tool_args.get("name") or tool_args.get("query") or "").strip()
        return open_app(app_name)
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
    compact_memories = [str(m)[:180] for m in memories[:2]]
    memory_ctx = ("\n[MEMORY]\n" + "\n".join(f"- {m}" for m in compact_memories)) if compact_memories else ""

    compact_history = []
    for message in session_history[-4:]:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "user") or "user")
        content = str(message.get("content", "") or "")[:320]
        compact_history.append({"role": role, "content": content})

    # Detect if Groq is in cooldown (rate-limited or unavailable)
    groq_unavailable = time.time() < _groq_cooldown_until or client is None
    local_mode_active = groq_unavailable

    messages = [
        {"role": "system", "content": f"{build_system_prompt(memory_ctx, local_mode_active=local_mode_active)}\n\n{SYSTEM_PROMPT}".strip()},
        *compact_history,
        {"role": "user", "content": user_input},
    ]

    if stream_sink:
        stream_sink("status", {"state": "thinking"})

    lower_input = user_input.strip().lower()
    if "map" in lower_input and ("open" in lower_input or "google" in lower_input):
        match = re.search(r"(?:map|maps)(?:\s+and\s+open\s+the)?\s+(.+?)(?:\s+location)?$", user_input, flags=re.IGNORECASE)
        location = (match.group(1) if match else user_input).strip()
        for token in ["open", "google", "map", "maps", "and", "the"]:
            location = re.sub(rf"\b{token}\b", " ", location, flags=re.IGNORECASE)
        location = " ".join(location.split()).strip() or "current location"
        map_url = f"https://www.google.com/maps/search/{quote_plus(location)}"
        try:
            tool_out = await _call_tool("open_url", {"url": map_url, "query": location})
            reply = f"Opened Google Maps for {location}, sir."
            memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
            return {"reply": reply, "tool_used": "open_url", "tool_result": tool_out}
        except Exception as exc:
            logger.warning("Deterministic maps intent failed: %s", exc)

    # Deterministic time query handler — always call get_system_stats for time/date queries
    if re.search(r"\b(time|date|what time|current time|what's the time|what is the time)\b", lower_input):
        try:
            tool_out = await _call_tool("get_time", {})
            reply = f"{tool_out}, sir."
            memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
            return {"reply": reply, "tool_used": "get_time", "tool_result": tool_out}
        except Exception as exc:
            logger.warning("Deterministic time intent failed: %s", exc)

    # Deterministic search/open URL handler — for "open github", "search X", etc.
    search_match = re.search(r"\b(?:open|search|go to|visit)\s+(\S+.*?)$", lower_input)
    if search_match:
        query = search_match.group(1).strip()
        if query and not re.search(r"\b(app|open app)\b", query):
            # Map common searches to URLs
            search_urls = {
                "github": "https://github.com/search?q=",
                "google": "https://www.google.com/search?q=",
                "bing": "https://www.bing.com/search?q=",
                "youtube": "https://www.youtube.com/results?search_query=",
                "stackoverflow": "https://stackoverflow.com/search?q=",
                "reddit": "https://www.reddit.com/search/?q=",
            }
            
            # Find matching search engine
            search_engine = None
            search_terms = query
            for engine, base_url in search_urls.items():
                if engine in query.lower():
                    search_engine = engine
                    search_terms = query.lower().replace(engine, "").strip()
                    url = base_url + quote_plus(search_terms or "")
                    break
            
            if search_engine:
                try:
                    tool_out = await _call_tool("open_url", {"url": url, "query": search_terms})
                    reply = f"Opening {search_engine} search for '{search_terms}', sir."
                    memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
                    return {"reply": reply, "tool_used": "open_url", "tool_result": tool_out}
                except Exception as exc:
                    logger.warning("Deterministic search intent failed: %s", exc)

    if client is None:
        reply = await _local_chat_completion(messages) or _offline_reply(user_input)
        memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
        return {"reply": reply, "tool_used": None, "tool_result": None}

    try:
        tool_specs = await _get_dynamic_tools()
        allowed_tools = {tool["function"]["name"] for tool in tool_specs if tool.get("function", {}).get("name")}
        response = _chat_completion(messages, allow_tools=True, tools=tool_specs)
    except Exception as exc:
        recovered_tool = _extract_failed_generation(exc, allowed_tools if "allowed_tools" in locals() else set())
        if recovered_tool:
            tool_used, tool_args = recovered_tool
            try:
                tool_result = await _call_tool(tool_used, tool_args)
                reply = f"Completed {tool_used} successfully, sir."
                memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
                return {"reply": reply, "tool_used": tool_used, "tool_result": tool_result}
            except Exception as tool_exc:
                logger.warning("Recovered failed_generation tool execution failed: %s", tool_exc)

        logger.warning("Tool-enabled chat failed; retrying without tools: %s", exc)
        try:
            response = _chat_completion(messages, allow_tools=False)
        except Exception as retry_exc:
            logger.warning("Plain Groq retry failed: %s", retry_exc)
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
    else:
        fallback_tool = _extract_tool_request(msg.content or "", allowed_tools)
        if fallback_tool:
            tool_used, tool_args = fallback_tool
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
                threading.Thread(target=lambda: asyncio.run(speak(reply)), daemon=True).start()

            return {"reply": reply, "tool_used": None, "tool_result": None}

    if stream_sink:
        stream_sink("tool_execute", {"tool": tool_used, "arguments": tool_args})

    try:
        tool_result = await _call_tool(tool_used, tool_args)
    except Exception as exc:
        tool_result = f"Tool error: {exc}"

    if stream_sink:
        stream_sink("tool_result", {"tool": tool_used, "status": "completed", "output": tool_result})

    if msg.tool_calls:
        messages.append({"role": "assistant", "content": None, "tool_calls": msg.tool_calls})
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": _stringify_result(tool_result)})
    else:
        messages.append({"role": "assistant", "content": msg.content or ""})
        messages.append({"role": "tool", "content": _stringify_result(tool_result), "name": tool_used})

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