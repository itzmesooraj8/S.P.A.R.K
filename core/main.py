import json
import logging
import sys
import warnings
import os
import re
from typing import Dict, Any
from datetime import datetime

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

import keyboard
import pyperclip
import win32gui
from groq import Groq

from audio.stt import SparkEars
from audio.tts import SparkVoice
from core.tools import SparkTools
from core.memory import SparkMemory

# ---------------------------------------------------------------------------
# S.P.A.R.K. CORE ARCHITECTURE (Mark II Readiness)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", 
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SPARK_CORE")

def get_situational_awareness():
    try:
        window = win32gui.GetWindowText(win32gui.GetForegroundWindow())
        clipboard = pyperclip.paste()
        if len(clipboard) > 500: clipboard = clipboard[:500] + "..."
        return window, clipboard
    except Exception:
        return "Unknown", "Empty"

def execute_tool(command_json: Dict[str, Any], tools: SparkTools, voice: SparkVoice) -> str:
    """OODA ACT Node: Includes post-action verification (future vision hook)."""
    tool_name = command_json.get("tool")
    arg = command_json.get("arg", "")
    logger.info(f"OODA ACT: {tool_name}({arg})")
    
    try:
        if tool_name == "open_website": response = tools.open_website(arg)
        elif tool_name == "get_time": response = tools.get_time()
        elif tool_name == "open_application": response = tools.open_application(arg)
        elif tool_name == "read_clipboard": response = tools.read_clipboard()
        elif tool_name == "write_clipboard": response = tools.write_clipboard(arg)
        elif tool_name == "take_screenshot": response = tools.take_screenshot()
        elif tool_name == "type_text": response = tools.type_text(arg)
        else: response = f"Tool '{tool_name}' not configured."
        
        voice.speak(response)
        
        # --- POST-ACTION VERIFICATION LOOP ---
        # If it's a critical navigation action, we'd take a screenshot here
        if tool_name in ["open_website", "open_application"]:
            logger.info("Triggering post-action verification (Simulated)")
            # In Phase 02, we'd send tools.take_screenshot() to a Vision model
            
        return response
    except Exception as e:
        logger.error(f"Act Error: {e}")
        return "I encountered a physical obstruction executing that task, sir."

def main():
    logger.info("Initializing S.P.A.R.K. Mark I (Bug-Fixed Architecture)...")
    
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.critical("FATAL: GROQ_API_KEY missing.")
        sys.exit(1)

    try:
        groq_client = Groq(api_key=api_key)
        ears = SparkEars()
        voice = SparkVoice()
        tools = SparkTools()
        memory = SparkMemory()
    except Exception as e:
        logger.critical(f"Initialization failure: {e}")
        sys.exit(1)
        
    voice.speak("S.P.A.R.K. systems online. Ready for your command, Sooraj.")
    
    try:
        while True:
            logger.info("System idling. Awaiting OODA trigger (F9).")
            keyboard.wait('f9')
            
            memory.cursor.execute('DELETE FROM conversation') 
            memory.conn.commit()
            voice.speak("Yes, Sooraj?")
            
            while True:
                user_input = ears.listen() 
                
                # --- 1. THE OBSERVE FILTERS ---
                if user_input == "TIMEOUT":
                    logger.info("Observation timeout. Auto-sleeping.")
                    voice.speak("Standing by, sir.")
                    break 
                
                # CONFIDENCE GATE: Handle noisy input by asking for repeat
                if user_input == "LOW_CONFIDENCE":
                    voice.speak("Didn't catch that clearly, sir — could you repeat?")
                    continue
                    
                if not user_input:
                    continue
                    
                logger.info(f"User: {user_input}")
                
                # --- 2. ORIENT ---
                active_window, clipboard_data = get_situational_awareness()
                current_time = datetime.now().strftime("%I:%M %p")
                recent_history = memory.get_context_string(limit=4)
                
                # REFINED SYSTEM PROMPT (Structured JSON Enforcement)
                system_prompt = f"""You are S.P.A.R.K. (Synthetic Personal Autonomous Reasoning Kernel), a highly intelligent AI assistant created by Sooraj.
Persona: Dry wit, absolute loyalty, professional tone. Honorific: 'Sir'.

[SITUATIONAL AWARENESS]
Time: {current_time}
Active Window: {active_window}
Clipboard: {clipboard_data}

[MISSION CRITICAL]
- If input is nonsensical or noisy, say: "I'm sorry, I didn't catch that clearly."
- For ACTIONS, output ONLY valid JSON.
- Example: {{"tool": "open_website", "arg": "youtube"}}
- Do NOT use placeholder arguments like 'site_name' or 'url_here'. Use real data.
- Tools: open_website, get_time, open_application, read_clipboard, write_clipboard, take_screenshot, type_text."""

                messages = [{"role": "system", "content": system_prompt}]
                if recent_history:
                    messages.append({"role": "system", "content": f"Previous context:\n{recent_history}"})
                messages.append({"role": "user", "content": user_input})

                # --- 3. DECIDE ---
                try:
                    completion = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=messages,
                        temperature=0.6,
                        max_tokens=500,
                    )
                    
                    answer = completion.choices[0].message.content.strip()
                    
                    # Tool Interceptor
                    if "{" in answer and "}" in answer:
                        try:
                            start = answer.find("{")
                            end = answer.rfind("}") + 1
                            command_json = json.loads(answer[start:end])
                            tool_result = execute_tool(command_json, tools, voice)
                            memory.remember("User", user_input)
                            memory.remember("S.P.A.R.K.", f"[Action] {tool_result}")
                            continue 
                        except json.JSONDecodeError:
                            pass
                            
                    memory.remember("User", user_input)
                    memory.remember("S.P.A.R.K.", answer)
                    voice.speak(answer)
                    
                except Exception as e:
                    logger.error(f"Decision Error: {e}")
                    voice.speak("I encountered a cognitive error in my reasoning circuits, sir.")

    except KeyboardInterrupt: sys.exit(0)

if __name__ == "__main__":
    main()
