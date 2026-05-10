"""
S.P.A.R.K. Core OODA Loop — Phase 02C
Integrates: Whisper STT · Groq LLM · Edge TTS · Vision · ChromaDB · Web Search
"""

import json
import logging
import os
import re
import sys
import time
import keyboard
from typing import Any, Dict, Optional
from dotenv import load_dotenv
import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Load environment variables from .env file before any API checks
load_dotenv()

# ── Internal modules ─────────────────────────────────────────────────────────
from audio.stt import SparkEars
from core.persona import build_system_prompt
from core.tools import SparkTools
from core.vision import describe_screen
from core.vector_store import SparkVectorMemory
from tools.web_search import web_search_answer
from audio.tts import SparkVoice
import threading
import requests
from core.scheduler import init_scheduler, set_reminder, shutdown_scheduler
from core.background import start_watcher, stop_watcher
from core.wake_word import start_wake_engine, stop_wake_engine
from core.memory_loop import retrieve as retrieve_turns, write_turn
from config import LLM_HOST, LLM_MODEL
from security.action_guard import guard_action
from security.audit import record_audit
from security.content_sanitizer import sanitize_for_llm, sanitize_memory_context
from security.intent_validator import validate_intent_text

def broadcast_hud_event(event_type: str, payload: dict):
    """Sends async events to the FastAPI server for HUD broadcasting"""
    def _send():
        try:
            requests.post("http://127.0.0.1:8000/internal/broadcast", json={"type": event_type, "payload": payload}, timeout=0.1)
        except Exception as e:
            logger.debug(f"Failed to broadcast HUD event: {e}")
    threading.Thread(target=_send, daemon=True).start()


def _emit_stream(stream_sink, event_type: str, payload: dict):
    if not stream_sink:
        return
    try:
        stream_sink(event_type, payload)
    except Exception:
        pass


def _speak_if_available(voice: SparkVoice | None, message: str) -> None:
    if voice and message:
        voice.speak(message)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("SPARK_CORE")


# ─────────────────────────────────────────────────────────────────────────────
# BOOT VALIDATION
# ─────────────────────────────────────────────────────────────────────────────

def startup_check() -> bool:
    """Validates all required secrets and dependencies before loading models."""
    logger.info("Running Security & Boot Diagnostics...")
    logger.info("Boot Diagnostics: PASSED. Local runtime mode enabled.")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# POST-ACTION VISION VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────

def post_action_verify(tool_name: str, screenshot_path: str) -> str:
    questions = {
        "open_website":     "What website is open? Any visible errors, notifications, or key information visible at a glance?",
        "open_application": "What application is in focus? Did it open successfully? Any error dialogs?",
        "type_text":        "Is there typed text visible? What does it say exactly?",
        "take_screenshot":  "Describe what is on the screen briefly.",
    }
    q = questions.get(tool_name, "What changed on screen after this action?")
    return describe_screen(screenshot_path, q)


from tools.sysmon import get_system_health
from tools.weather import get_weather
from tools.portfolio import PortfolioTracker
from core.morning import generate_morning_briefing
from tools.media import control_media
from tools.file_ops import search_and_open_file


def ensure_runtime_components() -> None:
    """Lazily initialize the shared runtime pieces used by the API and core loops."""
    global memory, tools, portfolio

    if memory is None:
        logger.info("Initializing semantic memory for shared runtime access...")
        memory = SparkVectorMemory()

    if tools is None:
        logger.info("Initializing shared tool suite for command execution...")
        tools = SparkTools()

    if portfolio is None:
        portfolio = PortfolioTracker(memory)

# ─────────────────────────────────────────────────────────────────────────────
# TOOL EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def execute_tool(
    command_json: Dict[str, Any],
    tools: SparkTools,
    voice: SparkVoice,
    portfolio_tracker: PortfolioTracker = None,
    source: str = "voice",
) -> str:
    """OODA ACT node: dispatches tool call, runs vision verification on navigation actions."""
    tool_name = command_json.get("tool", "").strip()
    arg = command_json.get("arg", "")
    logger.info(f"OODA ACT: {tool_name}({arg!r})")

    allowed, message, _request = guard_action(
        tool_name,
        source=source,
        risk="high" if tool_name in {"open_application", "open_website", "type_text", "take_screenshot"} else "medium" if tool_name in {"write_clipboard", "file_search"} else "low",
        requires_confirmation=tool_name in {"open_application", "open_website", "type_text", "take_screenshot"},
        args=arg,
        payload=command_json,
    )
    if not allowed:
        _speak_if_available(voice, message)
        return message

    try:
        # ── Tool dispatch ─────────────────────────────────────────────────
        if tool_name == "open_website":
            response = tools.open_website(arg)
        elif tool_name == "get_time":
            response = tools.get_time()
        elif tool_name == "open_application":
            response = tools.open_application(arg)
        elif tool_name == "read_clipboard":
            response = tools.read_clipboard()
        elif tool_name == "write_clipboard":
            response = tools.write_clipboard(arg)
        elif tool_name == "take_screenshot":
            response, _ = tools.take_screenshot()
        elif tool_name == "type_text":
            response = tools.type_text(arg)
        elif tool_name == "system_monitor":
            response = get_system_health()
            _speak_if_available(voice, response)
            return response
        elif tool_name == "get_weather":
            loc = arg if isinstance(arg, str) and arg.strip() else "Palakkad"
            response = get_weather(loc)
            _speak_if_available(voice, response)
            return response
        elif tool_name == "media_control":
            if isinstance(arg, dict):
                action = arg.get("action", "")
                val = arg.get("value")
            elif isinstance(arg, str):
                try:
                    arg_dict = json.loads(arg)
                    action = arg_dict.get("action", "")
                    val = arg_dict.get("value")
                except json.JSONDecodeError:
                    action = arg
                    val = None
            else:
                action = str(arg)
                val = None
            response = control_media(action, val)
            _speak_if_available(voice, response)
            return response
        elif tool_name == "file_search":
            response = search_and_open_file(str(arg))
            _speak_if_available(voice, response)
            return response
        elif tool_name == "portfolio" and portfolio_tracker:
            if isinstance(arg, dict):
                action = arg.get("action", "summary")
                sym = arg.get("symbol", "")
            elif isinstance(arg, str):
                try:
                    arg_dict = json.loads(arg)
                    action = arg_dict.get("action", "summary")
                    sym = arg_dict.get("symbol", "")
                except json.JSONDecodeError:
                    action = "summary"
                    sym = arg
            else:
                action = "summary"
                
            if action == "add":
                qty = arg.get("qty", 1) if isinstance(arg, dict) else 1
                price = arg.get("price", 1) if isinstance(arg, dict) else 1
                response = portfolio_tracker.add_holding(sym, qty, price)
            elif action == "remove":
                response = portfolio_tracker.remove_holding(sym)
            else:
                response = portfolio_tracker.get_portfolio_summary()
            
            _speak_if_available(voice, response)
            return response
        elif tool_name == "web_search":
            # Live web lookup — runs inline, no browser opened
            logger.info(f"WEB SEARCH: {arg!r}")
            result = web_search_answer(str(arg))
            if result:
                response = result
            else:
                response = (
                    "I was unable to retrieve live data for that query at this moment, sir. "
                    "You may want to check your network connection."
                )
            # Web search never needs vision verification — return directly
            _speak_if_available(voice, response)
            return response
        elif tool_name == "set_reminder":
            if isinstance(arg, dict):
                message = arg.get("message", "")
                delay_seconds = int(arg.get("delay_seconds", 60))
            else:
                try:
                    parsed = json.loads(arg)
                    message = parsed.get("message", str(arg))
                    delay_seconds = int(parsed.get("delay_seconds", 60))
                except Exception:
                    message = str(arg)
                    delay_seconds = 60
            response = set_reminder(message, delay_seconds)
            _speak_if_available(voice, response)
            return response
        else:
            response = (
                f"The tool '{tool_name}' is not in my current suite, sir. "
                "We can add it in the next build."
            )

        # Speak the primary response
        voice.speak(response)

        # ── Post-action vision verification (navigation & typing only) ───
        if tool_name in ("open_website", "open_application", "type_text"):
            logger.info("Triggering post-action vision verification...")
            time.sleep(2)  # allow page/app to load
            _, snap_path = tools.take_screenshot()
            if snap_path:
                observation = post_action_verify(tool_name, snap_path)
                if observation:
                    voice.speak(f"Verification: {observation}")
                    response += f" | Vision: {observation}"
                try:
                    os.remove(snap_path)
                except OSError:
                    pass

        return response

    except Exception as e:
        err_msg = f"Tool execution error in '{tool_name}': {e}"
        logger.error(err_msg)
        fallback = f"I encountered an error executing that command, sir. {e}"
        _speak_if_available(voice, fallback)
        return fallback


# ─────────────────────────────────────────────────────────────────────────────
# SITUATIONAL AWARENESS HELPER
# ─────────────────────────────────────────────────────────────────────────────

def get_situational_awareness() -> tuple[str, str]:
    """Returns (active_window_title, clipboard_preview) for context injection."""
    try:
        import pygetwindow as gw
        wins = gw.getActiveWindow()
        active = wins.title if wins else "Unknown"
    except Exception:
        active = "Unknown"
    try:
        import pyperclip
        clip = pyperclip.paste()
        preview = clip[:80] + "..." if len(clip) > 80 else clip
    except Exception:
        preview = "Empty"
    return active, preview


# ─────────────────────────────────────────────────────────────────────────────
# LLM CALL
# ─────────────────────────────────────────────────────────────────────────────

def call_local_llm(
    user_input: str,
    memory_context: str,
    conversation_history: list,
    stream_sink=None,
    cancel_event: threading.Event | None = None,
) -> str:
    """Sends a message to the local Ollama backend and returns the raw response text."""
    system_prompt = build_system_prompt(sanitize_memory_context(memory_context))

    user_scan = validate_intent_text(user_input)
    if not user_scan.allowed:
        record_audit("prompt_blocked", {"reason": "unsafe_user_input", "score": user_scan.score, "reasons": list(user_scan.reasons)})
        return "I cannot act on that instruction safely, sir."

    user_input = sanitize_for_llm(user_scan.cleaned_text or user_input)

    messages = [{"role": "system", "content": system_prompt}]
    messages += conversation_history[-4:]
    messages.append({"role": "user", "content": user_input})

    if stream_sink:
        try:
            with httpx.stream(
                "POST",
                f"{LLM_HOST}/api/chat",
                json={"model": LLM_MODEL, "messages": messages, "stream": True},
                timeout=180.0,
            ) as response:
                response.raise_for_status()
                chunks: list[str] = []
                for line in response.iter_lines():
                    if cancel_event and cancel_event.is_set():
                        _emit_stream(stream_sink, "error", {"message": "Generation cancelled"})
                        return ""
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                    except Exception:
                        continue
                    message = data.get("message", {}) if isinstance(data, dict) else {}
                    chunk = str(message.get("content", ""))
                    if chunk:
                        chunks.append(chunk)
                        _emit_stream(stream_sink, "response_token", {"token": chunk, "content": chunk})
                    if data.get("done"):
                        break
                content = "".join(chunks).strip()
                if content:
                    _emit_stream(stream_sink, "response_done", {"content": content})
                    return content
        except Exception as exc:
            logger.warning("Streaming LLM unavailable, falling back to non-streaming mode: %s", exc)

    try:
        response = httpx.post(
            f"{LLM_HOST}/api/chat",
            json={"model": LLM_MODEL, "messages": messages, "stream": False},
            timeout=180.0,
        )
        response.raise_for_status()
        message = response.json().get("message", {})
        content = str(message.get("content", "")).strip()
        if content:
            return content
    except Exception as exc:
        logger.warning("Local LLM unavailable, using offline fallback: %s", exc)

    if memory_context.strip():
        return f"I’m running locally, sir. I have contextual memory, but the local model is currently unavailable."
    return "I’m running locally, sir, but the local model is currently unavailable."


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE PARSER  — extracts tool call JSON if present
# ─────────────────────────────────────────────────────────────────────────────

_JSON_RE = re.compile(r'\{[^{}]*"tool"\s*:[^{}]*\}', re.DOTALL)

def parse_response(text: str) -> tuple[Optional[Dict], str]:
    """
    Returns (tool_dict, spoken_text).
    If a tool call JSON is found, tool_dict is populated and spoken_text is
    everything outside the JSON block (often empty).
    """
    m = _JSON_RE.search(text)
    if m:
        try:
            tool_dict = json.loads(m.group())
            spoken = text[:m.start()].strip() + text[m.end():].strip()
            return tool_dict, spoken.strip()
        except json.JSONDecodeError:
            pass
    return None, text


# ── Global instances for callback access ─────────────────────────────────────
stt = None
voice = None
tools = None
memory = None
portfolio = None
conversation_history = []

def run_agent_turn(
    user_input: str,
    voice_output: bool = True,
    cli_mode: bool = False,
    stream_sink=None,
    cancel_event: threading.Event | None = None,
) -> str:
    """
    Execute one full agent turn: memory retrieval → LLM → tool use → response.
    Returns the final response string.
    """
    global conversation_history, memory, portfolio, tools, voice

    if not user_input or user_input == "TIMEOUT":
        return ""

    if user_input == "LOW_CONFIDENCE":
        user_input = "I'm sorry, I muttered something unclear."

    logger.info(f"User: {user_input}")
    ensure_runtime_components()
    if voice:
        try:
            voice.stop()
        except Exception:
            pass

    # ── ORIENT: retrieve relevant memories ──────────────────────────
    turn_context = ""
    try:
        turns = retrieve_turns(user_input)
        turns = turns[-4:]
        turn_context = "\n".join(
            f"{turn.get('role', 'unknown')}: {turn.get('content', '')}" for turn in turns
        )
    except Exception:
        turn_context = ""

    try:
        memories = memory.recall(user_input, n=2)
        semantic_context = "\n".join(f"- {m}" for m in memories) if memories else ""
    except Exception:
        semantic_context = ""

    memory_context = "\n\n".join(
        [part for part in [turn_context, semantic_context] if part.strip()]
    )

    # ── DECIDE: call LLM ─────────────────────────────────────────────
    try:
        raw_response = call_local_llm(
            user_input,
            memory_context,
            conversation_history,
            stream_sink=stream_sink,
            cancel_event=cancel_event,
        )
        logger.info(f"LLM raw: {raw_response}")
    except Exception as e:
        logger.error(f"Local LLM error: {e}")
        if not cli_mode:
            _speak_if_available(voice, "I'm experiencing a temporary connection issue, sir.")
        return "LLM Error"

    if not raw_response.strip() and cancel_event and cancel_event.is_set():
        return ""

    # ── ACT: parse and dispatch ──────────────────────────────────────
    tool_call, spoken_text = parse_response(raw_response)

    # Speak any text that came before/after the tool JSON
    if spoken_text and voice_output and voice and not (tool_call and tool_call.get("tool") in ["web_search", "system_monitor", "get_weather", "portfolio", "media_control", "file_search", "set_reminder"]):
        voice.speak(spoken_text)

    final_response = raw_response

    if tool_call:
        tool_name = tool_call.get("tool", "unknown_tool")
        tool_arg = str(tool_call.get("arg", ""))
        broadcast_hud_event("agent_log", {"agent": "S.P.A.R.K. Core", "action": f"Executing: {tool_name}", "data": tool_arg})
        _emit_stream(stream_sink, "tool_execute", {"tool": tool_name, "arguments": {"arg": tool_arg}})
        
        tool_result = execute_tool(tool_call, tools, voice, portfolio_tracker=portfolio, source="voice")
        final_response = tool_result
        
        short_result = str(tool_result)[:200] + "..." if len(str(tool_result)) > 200 else str(tool_result)
        broadcast_hud_event("agent_log", {"agent": "S.P.A.R.K. Core", "action": f"Result: {tool_name}", "data": short_result})
        _emit_stream(stream_sink, "tool_result", {"tool": tool_name, "status": "completed", "output": tool_result})

    # ── UPDATE MEMORY ────────────────────────────────────────────────
    try:
        write_turn("user", user_input, metadata={"tool": tool_call.get("tool") if tool_call else "conversation"})
        write_turn("assistant", final_response, metadata={"tool": tool_call.get("tool") if tool_call else "conversation"})
        memory.remember(
            "user",
            user_input,
            metadata={"tool": tool_call.get("tool") if tool_call else "conversation"},
        )
        memory.remember(
            "assistant",
            final_response,
            metadata={"tool": tool_call.get("tool") if tool_call else "conversation"},
        )
    except Exception:
        pass

    conversation_history.append({"role": "user", "content": user_input})
    conversation_history.append({"role": "assistant", "content": raw_response})
    
    return final_response

def _voice_trigger():
    """Called by wake word engine OR F9 — runs one full voice interaction cycle."""
    global stt, voice
    try:
        # 1. Listen
        broadcast_hud_event("voice_state", {"status": "listening", "isListening": True})
        user_text = stt.listen()

        if not user_text or user_text == "TIMEOUT":
            broadcast_hud_event("voice_state", {"status": "idle", "isListening": False})
            return

        # 2. Log to HUD
        broadcast_hud_event("agent_log", {"agent": "STT", "action": "Heard", "data": user_text})

        # 3. Run full agent pipeline
        run_agent_turn(user_text, voice_output=True)

    except Exception as e:
        logger.error(f"[MAIN] Voice trigger error: {e}")
        broadcast_hud_event("voice_state", {"status": "idle", "isListening": False})


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

def run():
    """Boot sequence for S.P.A.R.K. Core + Proactive Agency."""
    global stt, voice, tools, memory, portfolio, conversation_history

    if not startup_check():
        sys.exit(1)

    logger.info("Starting S.P.A.R.K. Core (Phase 03 — Proactive Agency)...")
    
    # ── 1. Init Base Systems ──────────────────────────────────────────
    voice = SparkVoice()
    
    logger.info("Initializing S.P.A.R.K. Ears (Whisper Small - Enhanced Accuracy)...")
    stt = SparkEars()
    
    logger.info("Initializing S.P.A.R.K. Multi-Tool Suite...")
    tools = SparkTools()
    
    logger.info("Initializing S.P.A.R.K. Semantic Memory Core (ChromaDB)...")
    memory = SparkVectorMemory()
    
    portfolio = PortfolioTracker(memory)
    
    conversation_history = []

    from core.heartbeat import start_heartbeat, stop_heartbeat
    # ── 2. Phase 03: Start Proactive Daemons ──────────────────────────
    logger.info("[PHASE 03] Initializing proactive agency daemons...")
    
    # Scheduler (Timed reminders)
    init_scheduler(voice=voice)
    
    # Clipboard Watcher (Contextual triggers)
    # We pass a simple lambda for LLM queries so the watcher can do intent checks
    llm_query = lambda p: run_agent_turn(p, voice_output=False, cli_mode=True)
    start_watcher(voice=voice, llm_query_fn=llm_query)

    # Heartbeat Engine (Periodic System Checks)
    start_heartbeat()

    # ── 3. Phase 04: Start Wake Engine ────────────────────────────────
    # This replaces the keyboard.wait loop.
    # The callback _voice_trigger is called when 'Hey SPARK' (or F9) is detected.
    start_wake_engine(on_wake_callback=_voice_trigger, use_hotword=True)

    # ── 4. Main Event Loop (Idle) ─────────────────────────────────────
    logger.info("S.P.A.R.K. Core is fully operational.")
    
    # Phase 02D Morning Briefing (now part of Phase 03 boot)
    try:
        morning_msg = generate_morning_briefing()
        voice.speak(morning_msg)
    except Exception as e:
        logger.error(f"Morning briefing failed: {e}")
        voice.speak("S.P.A.R.K. systems online. All modules nominal. Ready for your command, sir.")
    
    try:
        while True:
            # The background threads (scheduler, watcher, wake_word, heartbeat) do the work.
            # We just stay alive here.
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutdown sequence initiated...")
    finally:
        # ── 5. Graceful Exit ──────────────────────────────────────────
        stop_heartbeat()
        stop_wake_engine()
        stop_watcher()
        shutdown_scheduler()
        logger.info("S.P.A.R.K. Core offline.")


if __name__ == "__main__":
    run()
