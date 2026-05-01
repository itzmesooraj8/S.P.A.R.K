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

def broadcast_hud_event(event_type: str, payload: dict):
    """Sends async events to the FastAPI server for HUD broadcasting"""
    def _send():
        try:
            requests.post("http://127.0.0.1:8000/internal/broadcast", json={"type": event_type, "payload": payload}, timeout=0.1)
        except:
            pass
    threading.Thread(target=_send, daemon=True).start()

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
    required = ["GROQ_API_KEY"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        logger.critical(f"BOOT FAILED — Missing environment variables: {missing}")
        logger.critical("Set them in your .env file or system environment and restart.")
        return False
    logger.info("Boot Diagnostics: PASSED. Secrets verified.")
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

# ─────────────────────────────────────────────────────────────────────────────
# TOOL EXECUTION
# ─────────────────────────────────────────────────────────────────────────────

def execute_tool(
    command_json: Dict[str, Any],
    tools: SparkTools,
    voice: SparkVoice,
    portfolio_tracker: PortfolioTracker = None
) -> str:
    """OODA ACT node: dispatches tool call, runs vision verification on navigation actions."""
    tool_name = command_json.get("tool", "").strip()
    arg = command_json.get("arg", "")
    logger.info(f"OODA ACT: {tool_name}({arg!r})")

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
            voice.speak(response)
            return response
        elif tool_name == "get_weather":
            loc = arg if isinstance(arg, str) and arg.strip() else "Palakkad"
            response = get_weather(loc)
            voice.speak(response)
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
                except:
                    action = arg
                    val = None
            else:
                action = str(arg)
                val = None
            response = control_media(action, val)
            voice.speak(response)
            return response
        elif tool_name == "file_search":
            response = search_and_open_file(str(arg))
            voice.speak(response)
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
                except:
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
            
            voice.speak(response)
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
            voice.speak(response)
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
        voice.speak(fallback)
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

def call_groq(
    user_input: str,
    memory_context: str,
    conversation_history: list,
    groq_client,
) -> str:
    """Sends a message to Groq and returns the raw response text."""
    system_prompt = build_system_prompt(memory_context)

    messages = [{"role": "system", "content": system_prompt}]
    messages += conversation_history[-6:]  # keep last 3 turns
    messages.append({"role": "user", "content": user_input})

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=300,
        temperature=0.6,
    )
    return response.choices[0].message.content.strip()


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


# ─────────────────────────────────────────────────────────────────────────────
# MAIN LOOP
# ─────────────────────────────────────────────────────────────────────────────

def run():
    if not startup_check():
        sys.exit(1)

    logger.info("Initializing S.P.A.R.K. Mark I (Phase 02C — Web Intelligence)...")

    from groq import Groq
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    logger.info("Initializing S.P.A.R.K. Ears (Whisper Small - Enhanced Accuracy)...")
    stt = SparkEars()

    logger.info("Initializing S.P.A.R.K. Voice (Microsoft Edge TTS - FREE)...")
    voice = SparkVoice()

    logger.info("Initializing S.P.A.R.K. Multi-Tool Suite...")
    tools = SparkTools()

    logger.info("Initializing S.P.A.R.K. Semantic Memory Core (ChromaDB)...")
    memory = SparkVectorMemory()
    
    portfolio = PortfolioTracker(memory)

    conversation_history: list = []

    # Phase 02D Morning Briefing
    try:
        morning_msg = generate_morning_briefing()
        voice.speak(morning_msg)
    except Exception as e:
        logger.error(f"Morning briefing failed: {e}")
        voice.speak("S.P.A.R.K. systems online. All modules nominal. Ready for your command, sir.")
    
    while True:
        logger.info("System idling. Awaiting OODA trigger (F9).")
        keyboard.wait('f9')
        
        memory.clear_ephemeral()
        voice.speak("Yes, Sooraj?")

        while True:
            # ── OBSERVE: listen for voice input ─────────────────────────────
            user_input = stt.listen()
            
            if user_input == "TIMEOUT":
                logger.info("Observation timeout. Auto-sleeping.")
                voice.speak("Standing by, sir.")
                break 
            
            # The new persona law #4 says to interpret ambiguous input instead of dropping it entirely.
            # But if it's purely noise, we can still drop it or rely on LLM to handle it gracefully.
            if user_input == "LOW_CONFIDENCE":
                user_input = "I'm sorry, I muttered something unclear."
                
            if not user_input:
                continue

            logger.info(f"User: {user_input}")

            # ── ORIENT: retrieve relevant memories ──────────────────────────
            try:
                memories = memory.recall(user_input, n=3)
                memory_context = "\n".join(f"- {m}" for m in memories) if memories else ""
            except Exception:
                memory_context = ""

            # ── DECIDE: call LLM ─────────────────────────────────────────────
            try:
                raw_response = call_groq(user_input, memory_context, conversation_history, groq_client)
                logger.info(f"LLM raw: {raw_response}")
            except Exception as e:
                logger.error(f"Groq API error: {e}")
                voice.speak("I'm experiencing a temporary connection issue with my reasoning core, sir. Please try again in a moment.")
                continue

            # ── ACT: parse and dispatch ──────────────────────────────────────
            tool_call, spoken_text = parse_response(raw_response)

            # Speak any text that came before/after the tool JSON
            if spoken_text and not (tool_call and tool_call.get("tool") in ["web_search", "system_monitor", "get_weather", "portfolio", "media_control", "file_search"]):
                voice.speak(spoken_text)

            final_response = raw_response

            if tool_call:
                tool_name = tool_call.get("tool", "unknown_tool")
                tool_arg = str(tool_call.get("arg", ""))
                broadcast_hud_event("agent_log", {"agent": "S.P.A.R.K. Core", "action": f"Executing: {tool_name}", "data": tool_arg})
                
                tool_result = execute_tool(tool_call, tools, voice, portfolio_tracker=portfolio)
                final_response = tool_result
                
                # Truncate result for log to avoid massive strings (like web search HTML)
                short_result = str(tool_result)[:200] + "..." if len(str(tool_result)) > 200 else str(tool_result)
                broadcast_hud_event("agent_log", {"agent": "S.P.A.R.K. Core", "action": f"Result: {tool_name}", "data": short_result})

            # ── UPDATE MEMORY ────────────────────────────────────────────────
            try:
                memory.remember(
                    f"User: {user_input} | SPARK: {final_response[:150]}",
                    metadata={"tool": tool_call.get("tool") if tool_call else "conversation"}
                )
            except Exception:
                pass

            # Update conversation history for multi-turn context
            conversation_history.append({"role": "user", "content": user_input})
            conversation_history.append({"role": "assistant", "content": raw_response})


if __name__ == "__main__":
    run()
