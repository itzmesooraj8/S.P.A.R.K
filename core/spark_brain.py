"""S.P.A.R.K spark brain - Groq-native tool calling."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
import httpx
import json
import logging
import os
import psutil
import requests
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from urllib.parse import quote_plus
from typing import Any

from dotenv import load_dotenv
from groq import Groq
from core.generated_tools import load_generated_tool_specs, run_generated_tool
from core.intent_router import parse_intents
from config import LLM_HOST, LLM_MODEL
from core.persona import build_system_prompt
from core.tools import SparkTools
from spark.token_counter import TokenCounter

from core.memory import MemoryStore, MemoryCategory
from core.mcp_manager import MCPManager
from core.planner import spark_plan_and_execute
from core.local_brain_chain import local_chain_complete, chain_status
from security.schema_validator import validate_tool_arguments, extract_json_object

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
            "name": "run_swarm_task",
            "description": "Execute a task autonomously using a swarm of sandbox-bounded agents (Code Agent, File Agent, Research Agent). Use this for complex multi-step developer, file, or coding tasks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "Detailed goal or coding instruction for the swarm"}
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
    },
    {
        "type": "function",
        "function": {
            "name": "generate_workspace",
            "description": "Translate a code or website creation request into a structured JSON manifest and build/serve the result inside a sandboxed subfolder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_name": {
                        "type": "string",
                        "description": "Name of the project (no spaces, e.g. healthcare_portal)"
                    },
                    "prompt": {
                        "type": "string",
                        "description": "The user's original request details to build"
                    }
                },
                "required": ["project_name", "prompt"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "optimize_cad_topology",
            "description": "Optimize voxel topology for structural compliance using SIMP calculations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "volume_fraction": {
                        "type": "number",
                        "description": "Target volume fraction (between 0.01 and 1.0)"
                    },
                    "compliance_target": {
                        "type": "number",
                        "description": "Target compliance threshold"
                    }
                },
                "required": ["volume_fraction", "compliance_target"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "solve_robot_kinematics",
            "description": "Solve analytical inverse kinematics for a 3-DoF robotic arm using DH models.",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "number", "description": "Target X coordinate"},
                    "y": {"type": "number", "description": "Target Y coordinate"},
                    "z": {"type": "number", "description": "Target Z coordinate"}
                },
                "required": ["x", "y", "z"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_predictive_diagnostics",
            "description": "Analyze an acoustic audio stream of a spindle to detect chatter and predict system degradation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "audio_stream_path": {
                        "type": "string",
                        "description": "Path to the WAV audio file stream"
                    }
                },
                "required": ["audio_stream_path"]
            }
        }
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

        # Resolve sandbox path under workspace directory
        workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sandbox_path = os.path.join(workspace_dir, "sandbox")
        os.makedirs(sandbox_path, exist_ok=True)

        result = subprocess.run(
            [sys.executable, tmp_path],
            capture_output=True,
            text=True,
            timeout=15,
            cwd=sandbox_path,
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


def _summarize_result(result: Any, max_len: int = 160) -> str:
    """Return a concise human-friendly summary for tool results."""
    try:
        # Lists of dicts (e.g., web_search results)
        if isinstance(result, list) and result and isinstance(result[0], dict):
            parts = []
            for item in result[:3]:
                title = item.get("title") or item.get("name") or item.get("headline") or item.get("summary")
                url = item.get("link") or item.get("url") or item.get("uri")
                if title and url:
                    parts.append(f"{title} ({url})")
                elif title:
                    parts.append(str(title))
                elif url:
                    parts.append(str(url))
            summary = "; ".join(parts) if parts else _stringify_result(result[:2])
            return (summary[:max_len] + "...") if len(summary) > max_len else summary

        # Dicts: pretty json
        if isinstance(result, dict):
            keys = ", ".join(str(k) for k in list(result.keys())[:6])
            short = f"{{{keys}}}"
            return short if len(short) <= max_len else short[:max_len] + "..."

        # Strings and others
        s = _stringify_result(result)
        return (s[:max_len] + "...") if len(s) > max_len else s
    except Exception:
        return str(result)[:max_len]


def _format_weather_reply(weather_data: Any, location: str) -> str:
    if not isinstance(weather_data, dict):
        return _stringify_result(weather_data)

    error = str(weather_data.get("error") or "").strip()
    if error:
        return f"I couldn't get weather for {location}, sir. {error}"

    temperature = weather_data.get("temperature_c")
    humidity = weather_data.get("humidity_%")
    wind = weather_data.get("wind_kmh")

    temperature_text = f"{temperature}°C" if temperature is not None else "unknown"
    humidity_text = f"{humidity}%" if humidity is not None else "unknown"
    wind_text = f"{wind} km/h" if wind is not None else "unknown"

    condition = str(
        weather_data.get("condition")
        or weather_data.get("summary")
        or weather_data.get("description")
        or ""
    ).strip()

    parts = [
        f"Currently in {location}: {temperature_text}",
        f"humidity at {humidity_text}",
        f"wind at {wind_text}",
    ]
    if condition:
        parts.insert(1, condition)

    return ", ".join(parts) + ", sir."


def _is_greeting_input(text: str) -> bool:
    normalized = re.sub(r"[\s.!?,]+", " ", (text or "").strip().lower()).strip()
    return normalized in {
        "hi",
        "hii",
        "hiii",
        "hello",
        "hey",
        "yo",
        "sup",
        "good morning",
        "good afternoon",
        "good evening",
    }


def _intent_to_tool_call(intent: Any) -> tuple[str, dict[str, Any]] | None:
    action = str(getattr(intent, "action", "") or "").strip()
    target = str(getattr(intent, "target", "") or "").strip()
    params = getattr(intent, "params", {})
    params = params if isinstance(params, dict) else {}

    if action in {"", "respond"}:
        return None
    if action == "open_app":
        return "open_app", {"app": target}
    if action == "open_url_in_browser":
        url = target if re.match(r"^https?://", target, flags=re.IGNORECASE) else ""
        query = "" if url else target
        return "open_url", {"url": url, "query": query}
    if action == "web_search":
        return "web_search", {"query": target}
    if action == "get_weather":
        return "get_weather", {"location": target}
    if action == "get_time":
        return "get_time", {}
    if action == "open_url":
        return "open_url", {"url": target, "query": params.get("query", "") or target}
    return None


def _extract_tool_request(content: str, allowed_tools: set[str]) -> tuple[str, dict[str, Any]] | None:
    text = (content or "").strip()
    if not text:
        return None

    try:
        payload = extract_json_object(text)
    except Exception:
        payload = None

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

    validation = validate_tool_arguments(tool_args, tool_name=tool_name)
    if not validation.allowed:
        return None

    tool_args = validation.cleaned_payload
    if tool_name == "execute_python" and isinstance(payload.get("value"), str) and not tool_args:
        tool_args = {"code": str(payload.get("value") or "")}

    return tool_name, tool_args


def _coerce_tool_arguments(raw_arguments: str | dict[str, Any] | None) -> dict[str, Any]:
    validation = validate_tool_arguments(raw_arguments)
    return validation.cleaned_payload if validation.allowed else {}


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


def _ollama_model_candidates(primary_model: str) -> list[str]:
    """Return local Ollama model candidates, preferring the configured primary model first."""
    candidates: list[str] = []
    seen: set[str] = set()

    def _add(model_name: str) -> None:
        normalized = model_name.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            candidates.append(normalized)

    _add(primary_model)

    try:
        response = requests.get(f"{LLM_HOST}/api/tags", timeout=3)
        response.raise_for_status()
        data = response.json()
        models = data.get("models", []) if isinstance(data, dict) else []
        if isinstance(models, list):
            sorted_models = sorted(
                [model for model in models if isinstance(model, dict)],
                key=lambda model: float(model.get("size", 0) or 0),
            )
            for model in sorted_models:
                _add(str(model.get("name") or model.get("model") or ""))
    except Exception:
        pass

    return candidates


def _ollama_prompt_from_messages(messages: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for message in messages:
        if not isinstance(message, dict):
            continue
        role = str(message.get("role", "user") or "user").strip().lower()
        content = str(message.get("content", "") or "").strip()
        if not content:
            continue
        if role == "system":
            parts.append(f"[SYSTEM]\n{content}")
        elif role == "assistant":
            parts.append(f"[ASSISTANT]\n{content}")
        else:
            parts.append(f"[USER]\n{content}")
    return "\n\n".join(parts)


def _local_http_completion(messages: list[dict[str, Any]]) -> str:
    """Call Ollama via persistent HTTP API for faster, local-only responses.
    
    This bypasses subprocess spawning and uses the persistent Ollama HTTP server.
    Perfect for fallback when Groq is in cooldown or unavailable.
    
    Args:
        messages: Full message list including system prompt
        
    Returns:
        Response text from local Ollama model
    """
    import requests
    
    timeout = float(os.getenv("SPARK_OLLAMA_HTTP_TIMEOUT_SECONDS", "10"))
    primary_timeout = float(os.getenv("SPARK_OLLAMA_PRIMARY_TIMEOUT_SECONDS", "5"))
    model = os.getenv("OLLAMA_MODEL", LLM_MODEL)
    prompt = _ollama_prompt_from_messages(messages)
    
    try:
        _ensure_local_ollama()
    except Exception as exc:
        logger.debug(f"Ollama startup probe failed: {exc}")

    for candidate in _ollama_model_candidates(model):
        candidate_timeout = primary_timeout if candidate == model else min(timeout, 25.0)

        for endpoint, body in (
            ("chat", {"model": candidate, "messages": messages, "stream": False}),
            ("generate", {"model": candidate, "prompt": prompt, "stream": False}),
        ):
            try:
                response = requests.post(f"{LLM_HOST}/api/{endpoint}", json=body, timeout=candidate_timeout)
                response.raise_for_status()

                data = response.json()
                if isinstance(data, dict):
                    if "message" in data:
                        return str(data["message"].get("content", "")).strip()
                    if "response" in data:
                        return str(data["response"]).strip()
                return str(data).strip() if data else ""
            except requests.exceptions.Timeout:
                logger.warning(f"Ollama HTTP timeout after {candidate_timeout}s for model {candidate} via /api/{endpoint}")
                break
            except requests.exceptions.HTTPError as exc:
                status = getattr(exc.response, "status_code", None)
                body_text = ""
                try:
                    body_text = str(exc.response.text)
                except Exception:
                    pass
                if status == 400 and endpoint == "chat":
                    logger.debug(f"Ollama chat unsupported for {candidate}; trying generate: {body_text}")
                    continue
                logger.debug(f"Ollama HTTP error for model {candidate} via /api/{endpoint}: {exc}")
                break
            except Exception as exc:
                logger.debug(f"Ollama HTTP error for model {candidate} via /api/{endpoint}: {exc}")
                break

    return ""


def _local_cli_completion(prompt: str, messages: list[dict[str, Any]] | None = None) -> str:
    """Run local Ollama model via CLI as last resort fallback.
    
    Only used if HTTP fails. This spawns a fresh process, so it's slower but more reliable
    as a final fallback when Ollama server is unresponsive.
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
        
        timeout = float(os.getenv("SPARK_OLLAMA_CLI_TIMEOUT_SECONDS", "10"))
        model = os.getenv("OLLAMA_MODEL", LLM_MODEL)
        result = subprocess.run(
            ["ollama", "run", model, full_prompt],
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
    """
    Run the 3-model local brain chain: gemma4 → qwen2.5 → qwen2.5:0.5b

    This is the single entry point for ALL local model calls in spark_brain.py.
    It replaces both _local_http_completion and _local_cli_completion.

    Called when:
      - Groq client is None (no API key)
      - Groq is in rate-limit cooldown
      - Daily token budget is exhausted
      - Groq call throws any exception
    """
    import asyncio

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        None,
        lambda: local_chain_complete(messages, auto_start=True, auto_pull=False),
    )

    if result.success:
        logger.info(
            "[LocalChain] Responded via %s (tried: %s)",
            result.model_used,
            ", ".join(result.attempts),
        )
    else:
        logger.warning(
            "[LocalChain] All models failed (tried: %s) — returning offline reply",
            ", ".join(result.attempts),
        )

    return result.text


class GroqFallbackError(RuntimeError):
    """Raised when Groq API encounters network, rate limit, or timeout issues requiring fallback to local LLM."""
    pass


def _chat_completion(messages: list[dict[str, Any]], allow_tools: bool = True, tools: list[dict[str, Any]] | None = None):
    # Double-check token budget before making ANY Groq call
    remaining_tokens = token_counter.get_remaining_today()
    if remaining_tokens < 5000:
        logger.warning(f"[token_guard] Blocking Groq call due to low budget: {remaining_tokens} tokens")
        raise GroqFallbackError(f"Daily Groq token budget too low ({remaining_tokens} < 5000); switching to Ollama-only mode")
    
    if time.time() < _groq_cooldown_until:
        raise GroqFallbackError("Groq is cooling down after rate limiting")

    if client is None:
        raise GroqFallbackError("Groq client is not initialized")

    import groq
    import httpx
    import requests

    from core.model_router import get_groq_model, validate_model
    groq_model = get_groq_model()
    if not validate_model(groq_model):
        raise GroqFallbackError(f"Model validation failed for '{groq_model}'. Model is not in predefined stable whitelists.")
    
    try:
        user_messages = [m.get("content") for m in messages if m.get("role") == "user" and m.get("content")]
        if user_messages:
            client.moderations.create(input=user_messages[-1])
    except Exception:
        pass

    kwargs: dict[str, Any] = {
        "model": groq_model,
        "messages": messages,
        "max_tokens": 1024,
        "user": "spark-operator",
    }
    if allow_tools:
        kwargs["tools"] = tools or TOOLS
        kwargs["tool_choice"] = "auto"

    retries = 3
    backoff = 1.0
    for attempt in range(retries):
        try:
            if kwargs.get("tools"):
                response = client.chat.completions.create(
                    model=groq_model,
                    messages=messages,
                    max_tokens=1024,
                    user="spark-operator",
                    tools=kwargs.get("tools"),
                    tool_choice=kwargs.get("tool_choice")
                )
            else:
                response = client.chat.completions.create(
                    model=groq_model,
                    messages=messages,
                    max_tokens=1024,
                    user="spark-operator"
                )
            
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
        except (
            groq.APIStatusError,
            groq.APIConnectionError,
            groq.APITimeoutError,
            httpx.TimeoutException,
            httpx.ConnectError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ) as exc:
            logger.warning(f"Groq API error on attempt {attempt + 1}: {exc}")
            _apply_rate_limit_cooldown(str(exc))
            if attempt == retries - 1:
                raise GroqFallbackError(f"Groq API failed after {retries} retries: {exc}") from exc
            time.sleep(backoff)
            backoff *= 2.0
        except Exception as exc:
            logger.warning(f"Groq API unexpected error: {exc}")
            raise GroqFallbackError(f"Groq API failed: {exc}") from exc



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
        try:
            response = _chat_completion(
                [
                    {"role": "system", "content": "You are SPARK's planning engine. Return only JSON."},
                    {"role": "user", "content": prompt},
                ],
                allow_tools=False,
            )
            msg = response.choices[0].message
            if hasattr(msg, "refusal") and msg.refusal:
                raise RuntimeError(f"Model refused request: {msg.refusal}")
            return (msg.content or "").strip()
        except GroqFallbackError as exc:
            logger.warning("GroqFallbackError in planner _sync_llm: %s. Falling back to local brain chain.", exc)
            import asyncio
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(_local_chat_completion([
                        {"role": "system", "content": "You are SPARK's planning engine. Return only JSON."},
                        {"role": "user", "content": prompt},
                    ]))
                finally:
                    loop.close()
            except Exception as local_exc:
                logger.error("Local chain fallback also failed in planner: %s", local_exc)
                raise RuntimeError(f"All model paths failed in planner: {local_exc}") from local_exc

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
    if tool_name == "run_swarm_task":
        return spark_tools.run_swarm_task(tool_args["goal"])
    if tool_name == "generate_workspace":
        from security.defense_interceptor import secure_generate_workspace
        return await secure_generate_workspace(tool_args.get("project_name", "project"), tool_args.get("prompt", ""))
    if tool_name == "optimize_cad_topology":
        from core.hardware_bridge import HardwareAgentBridge
        bridge = HardwareAgentBridge()
        return bridge.optimize_cad_topology(tool_args["volume_fraction"], tool_args["compliance_target"])
    if tool_name == "solve_robot_kinematics":
        from core.hardware_bridge import HardwareAgentBridge
        bridge = HardwareAgentBridge()
        return bridge.solve_robot_kinematics(tool_args["x"], tool_args["y"], tool_args["z"])
    if tool_name == "run_predictive_diagnostics":
        from core.hardware_bridge import HardwareAgentBridge
        bridge = HardwareAgentBridge()
        return bridge.run_predictive_diagnostics(tool_args["audio_stream_path"])
    if tool_name == "get_news":
        return get_news(tool_args["topic"])
    if tool_name == "get_weather":
        location = str(tool_args["location"]).strip()
        return _format_weather_reply(get_weather(location), location)
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


async def _try_multi_action_routing(user_input: str, parsed_intents: list[Any] | None = None) -> dict[str, Any] | None:
    """Detect and execute multi-action requests (e.g., "open app AND search query").
    
    Returns None if not a multi-action request or all actions fail.
    Otherwise returns execution result with summarized reply.
    
    This preprocessor runs BEFORE sending to Groq/LLM to enable fast local-only execution
    of sequential tool calls when user specifies explicit actions.
    """
    actions = parsed_intents if parsed_intents is not None else parse_intents(user_input)
    actionable = [action for action in actions if str(getattr(action, "action", "") or "").strip() not in {"", "respond"}]
    if len(actionable) < 2:
        return None

    logger.info(
        "[multi_action_routing] Executing %s sequential actions: %s",
        len(actionable),
        [str(getattr(action, "action", "") or "").strip() for action in actionable],
    )

    results: list[tuple[str, dict[str, Any], Any]] = []
    for action in actionable:
        tool_mapping = _intent_to_tool_call(action)
        if tool_mapping is None:
            continue

        tool_name, tool_args = tool_mapping
        try:
            result = await _call_tool(tool_name, tool_args)
            results.append((tool_name, tool_args, result))
            logger.debug("[multi_action_routing] %s completed: %s", tool_name, str(result)[:100])
        except Exception as exc:
            logger.warning("[multi_action_routing] %s failed: %s", tool_name, exc)
            results.append((tool_name, tool_args, f"Failed: {exc}"))

    if not results:
        logger.debug("[multi_action_routing] No executable actions resolved; falling back to conversational flow")
        return None
    
    # Summarize results
    summary_lines = []
    for tool_name, tool_args, result in results:
        result_str = _summarize_result(result, max_len=120) if result else "completed"
        summary_lines.append(f"• {tool_name}: {result_str}")
    
    reply = f"Completed {len(results)} actions:\n" + "\n".join(summary_lines)
    
    # Store in memory
    memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
    
    return {
        "reply": reply,
        "tool_used": f"{len(results)}_actions",
        "tool_result": [
            {"tool": tool_name, "args": tool_args, "result": result}
            for tool_name, tool_args, result in results
        ],
    }


async def _try_local_direct_tool_routing(user_input: str) -> dict[str, Any] | None:
    """Handle obvious single-action requests locally without waiting on Groq."""
    text = (user_input or "").strip()
    if not text:
        return None

    lower = text.lower()

    if re.search(r"\b(weather|forecast|temperature|rain|humidity)\b", lower):
        match = re.search(r"\b(?:in|for|at)\s+(.+)$", text, flags=re.IGNORECASE)
        location = (match.group(1) if match and match.group(1) else text)
        location = re.split(r"\b(?:and then|then|and|also|plus)\b|,", location, maxsplit=1, flags=re.IGNORECASE)[0]
        location = re.sub(r"\b(?:weather|forecast|temperature|what is|what's|is it|like|today|now|currently|the)\b", "", location, flags=re.IGNORECASE)
        location = re.sub(r"^\s*(?:in|for|at)\s+", "", location, flags=re.IGNORECASE).strip(" .") or "Palakkad"
        result = await _call_tool("get_weather", {"location": location})
        reply = f"Weather for {location}: {result}"
        memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
        return {"reply": reply, "tool_used": "get_weather", "tool_result": result}

    if re.search(r"\b(?:open|launch|start|run)\b", lower):
        if re.search(r"\b(map|maps|google maps)\b", lower):
            match = re.search(r"(?:map|maps)(?:\s+and\s+open\s+the)?\s+(.+?)(?:\s+location)?$", text, flags=re.IGNORECASE)
            location = (match.group(1) if match else text).strip()
            for token in ["open", "google", "map", "maps", "and", "the"]:
                location = re.sub(rf"\b{token}\b", " ", location, flags=re.IGNORECASE)
            location = " ".join(location.split()).strip() or "current location"
            map_url = f"https://www.google.com/maps/search/{quote_plus(location)}"
            result = await _call_tool("open_url", {"url": map_url, "query": location})
            reply = f"Opened Google Maps for {location}, sir."
            memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
            return {"reply": reply, "tool_used": "open_url", "tool_result": result}

        target = re.sub(r"^\s*(?:open|launch|start|run)\s+(?:the\s+|my\s+|app\s+|application\s+|program\s+)?", "", text, flags=re.IGNORECASE)
        target = re.split(r"\b(?:and then|then|and|also|plus)\b|,", target, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")
        if target:
            result = await _call_tool("open_app", {"app": target})
            reply = str(result)
            memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
            return {"reply": reply, "tool_used": "open_app", "tool_result": result}

    if re.search(r"\b(?:search|look up|lookup|find|research)\b", lower):
        query = re.sub(r"^\s*(?:search|look up|lookup|find|research)\s+", "", text, flags=re.IGNORECASE)
        query = re.split(r"\b(?:and then|then|and|also|plus)\b|,", query, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .")
        if query:
            result = await _call_tool("web_search", {"query": query})
            reply = f"Search results for {query}: {result}"
            memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
            return {"reply": reply, "tool_used": "web_search", "tool_result": result}

    return None


async def handle(user_input: str, session_history: list[dict[str, Any]], stream_sink=None, cancel_event=None) -> dict[str, Any]:
    from security.intent_validator import validate_intent_text
    
    # Run intent validation and conversational filler clean-up
    scan = validate_intent_text(user_input)
    if not scan.allowed:
        reply = "I cannot act on that instruction safely, sir."
        if stream_sink:
            stream_sink("response_done", {"content": reply})
        return {"reply": reply, "tool_used": None, "tool_result": None}
        
    if scan.cleaned_text and scan.cleaned_text.strip():
        user_input = scan.cleaned_text

    # Check token budget at session start - block Groq early if budget is low
    remaining_tokens = token_counter.get_remaining_today()
    if remaining_tokens < 5000:
        logger.warning(f"[token_guard] Groq budget low ({remaining_tokens} tokens) — routing to local")
        # Keep Groq on a shorter cooldown so the app can retry later in the day.
        global _groq_cooldown_until
        cooldown_seconds = int(os.getenv("SPARK_GROQ_LOW_BUDGET_COOLDOWN_SECONDS", "7200"))
        _groq_cooldown_until = max(_groq_cooldown_until, time.time() + cooldown_seconds)
    
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
    parsed_intents = parse_intents(user_input)
    actionable_intents = [intent for intent in parsed_intents if str(getattr(intent, "action", "") or "").strip() not in {"", "respond"}]
    compound_request = len(actionable_intents) > 1
    conversational_request = not actionable_intents

    if _is_greeting_input(user_input):
        greeting_hour = datetime.now().hour
        if greeting_hour < 12:
            greeting_prefix = "Good morning"
        elif greeting_hour < 17:
            greeting_prefix = "Good afternoon"
        else:
            greeting_prefix = "Good evening"
        reply = f"{greeting_prefix}, sir. How may I assist you today?"
        memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
        if stream_sink:
            stream_sink("response_done", {"content": reply})
        return {"reply": reply, "tool_used": None, "tool_result": None}

    if not compound_request and "map" in lower_input and ("open" in lower_input or "google" in lower_input):
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
    if not compound_request and re.search(r"\b(time|date|what time|current time|what's the time|what is the time)\b", lower_input):
        try:
            tool_out = await _call_tool("get_time", {})
            reply = f"{tool_out}, sir."
            memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
            return {"reply": reply, "tool_used": "get_time", "tool_result": tool_out}
        except Exception as exc:
            logger.warning("Deterministic time intent failed: %s", exc)

    if conversational_request:
        try:
            if client is None:
                reply = await _local_chat_completion(messages) or _offline_reply(user_input)
            else:
                response = _chat_completion(messages, allow_tools=False)
                msg = response.choices[0].message
                if hasattr(msg, "refusal") and msg.refusal:
                    reply = f"I am unable to fulfill that request: {msg.refusal}"
                else:
                    reply = (msg.content or "").strip() or _offline_reply(user_input)
        except GroqFallbackError:
            reply = await _local_chat_completion(messages) or _offline_reply(user_input)

        memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
        if stream_sink:
            stream_sink("response_done", {"content": reply})

        try:
            from tools.voice import speak
            asyncio.create_task(speak(reply))
        except RuntimeError:
            import threading
            from tools.voice import speak
            threading.Thread(target=lambda: asyncio.run(speak(reply)), daemon=True).start()

        return {"reply": reply, "tool_used": None, "tool_result": None}

    # Deterministic search/open URL handler — for "open github", "search X", etc.
    search_match = re.search(r"\b(?:open|search|go to|visit)\s+(\S+.*?)$", lower_input)
    if not compound_request and search_match:
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

    # Try multi-action routing for requests like "open app AND search query"
    # This provides fast local-only execution for composite requests
    try:
        multi_action_result = await _try_multi_action_routing(user_input, parsed_intents=parsed_intents)
        if multi_action_result:
            if stream_sink:
                stream_sink("response_done", {"content": multi_action_result["reply"]})
            return multi_action_result
    except Exception as exc:
        logger.debug(f"Multi-action routing failed (continuing with normal flow): {exc}")

    if not compound_request:
        try:
            local_tool_result = await _try_local_direct_tool_routing(user_input)
            if local_tool_result:
                if stream_sink:
                    stream_sink("response_done", {"content": local_tool_result["reply"]})
                return local_tool_result
        except Exception as exc:
            logger.debug(f"Local direct tool routing failed: {exc}")

    if client is None:
        reply = await _local_chat_completion(messages) or _offline_reply(user_input)
        memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
        return {"reply": reply, "tool_used": None, "tool_result": None}

    try:
        tool_specs = await _get_dynamic_tools()
        allowed_tools = {tool["function"]["name"] for tool in tool_specs if tool.get("function", {}).get("name")}
        response = _chat_completion(messages, allow_tools=True, tools=tool_specs)
    except GroqFallbackError as exc:
        logger.warning("Groq call failed with GroqFallbackError, routing directly to local fallback: %s", exc)
        reply = await _local_chat_completion(messages) or _offline_reply(user_input)
        memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
        if stream_sink:
            stream_sink("response_done", {"content": reply})
        return {"reply": reply, "tool_used": None, "tool_result": None}
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
        except (Exception, GroqFallbackError) as retry_exc:
            logger.warning("Plain Groq retry failed: %s", retry_exc)
            reply = await _local_chat_completion(messages) or _offline_reply(user_input)
            memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
            if stream_sink:
                stream_sink("response_done", {"content": reply})
            return {"reply": reply, "tool_used": None, "tool_result": None}

    msg = response.choices[0].message
    if hasattr(msg, "refusal") and msg.refusal:
        logger.warning(f"Groq API returned a refusal: {msg.refusal}")
        reply = f"I am unable to fulfill that request: {msg.refusal}"
        memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)
        if stream_sink:
            stream_sink("response_done", {"content": reply})
        return {"reply": reply, "tool_used": None, "tool_result": None}

    tool_used = None
    tool_result = None

    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        tool_used = tool_call.function.name
        validation = validate_tool_arguments(getattr(tool_call.function, "arguments", None), tool_name=tool_used)
        if not validation.allowed:
            logger.warning(f"Tool arguments validation failed for {tool_used}: {validation.reasons}")
            reply = f"I encountered an error: the arguments for tool {tool_used} were malformed."
            if stream_sink:
                stream_sink("response_done", {"content": reply})
            return {"reply": reply, "tool_used": tool_used, "tool_result": "Validation failed: tool_arguments_malformed"}
        tool_args = validation.cleaned_payload
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

        try:
            final = _chat_completion(messages, allow_tools=False)
            final_msg = final.choices[0].message
            if hasattr(final_msg, "refusal") and final_msg.refusal:
                reply = f"Refusal: {final_msg.refusal}"
            else:
                reply = (final_msg.content or "").strip()
        except (Exception, GroqFallbackError) as exc:
            logger.warning("Final tool-followup completion failed; using local fallback: %s", exc)
            reply = await _local_chat_completion(messages) or _offline_reply(user_input)
    else:
        reply = (msg.content or "").strip()
        tool_text = _stringify_result(tool_result)
        if tool_text:
            reply = f"{reply}\n{tool_text}".strip() if reply else tool_text

    memory.store(f"User: {user_input} | SPARK: {reply[:200]}", MemoryCategory.CONVERSATION)

    if stream_sink:
        stream_sink("response_done", {"content": reply})

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


async def spark_plan_and_execute(goal: str) -> dict[str, Any]:
    """Exposes main planning agent loop for the console interface."""
    return await _run_planner(goal)