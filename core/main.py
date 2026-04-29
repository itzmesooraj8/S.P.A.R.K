import json
import logging
import sys
import warnings
import os
from typing import Dict, Any

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

import keyboard
from groq import Groq # NEW: Import Groq

from audio.stt import SparkEars
from audio.tts import SparkVoice
from core.tools import SparkTools
from core.memory import SparkMemory

# ---------------------------------------------------------------------------
# ENTERPRISE LOGGING CONFIGURATION
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO, 
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s", 
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("SPARK_CORE")

def execute_tool(command_json: Dict[str, Any], tools: SparkTools, voice: SparkVoice) -> str:
    """Parse the LLM's JSON and trigger the physical system tool."""
    tool_name = command_json.get("tool")
    arg = command_json.get("arg", "")
    logger.info(f"Executing Tool: {tool_name} | Args: {arg}")
    
    try:
        if tool_name == "open_website": response = tools.open_website(arg)
        elif tool_name == "get_time": response = tools.get_time()
        elif tool_name == "open_application": response = tools.open_application(arg)
        else: response = "Tool not configured."
        voice.speak(response)
        return response
    except Exception as e:
        logger.error(f"Tool Error: {e}")
        return "System error during tool execution."

def main():
    """Main event loop for S.P.A.R.K. Groq-Powered Subsystems."""
    logger.info("Initializing S.P.A.R.K. Groq-Powered Subsystems...")
    
    # Check for the Free API Key
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.critical("FATAL: GROQ_API_KEY is missing from the .env file.")
        sys.exit(1)

    try:
        groq_client = Groq(api_key=api_key)
        ears = SparkEars()
        voice = SparkVoice()
        tools = SparkTools()
        memory = SparkMemory()
    except Exception as e:
        logger.critical(f"FATAL: {e}")
        sys.exit(1)
        
    voice.speak("S.P.A.R.K. systems online. Press F9 to initiate.")
    
    try:
        while True:
            # --- 1. THE IDLE STATE ---
            logger.info("System idling. 0% CPU. Awaiting F9 hotkey.")
            keyboard.wait('f9')
            
            memory.cursor.execute('DELETE FROM conversation') 
            memory.conn.commit()
            voice.speak("Yes, Sooraj?")
            
            # --- 2. THE CONVERSATION LOOP ---
            while True:
                user_input = ears.listen() 
                
                # If the ears return TIMEOUT, you stopped talking. Go back to sleep.
                if user_input == "TIMEOUT":
                    logger.info("No speech detected. Auto-sleeping.")
                    voice.speak("Standing by.")
                    break # Breaks the inner loop, goes back to F9 wait
                    
                # If it's a hallucination (None), silently listen again
                if not user_input:
                    continue
                    
                logger.info(f"User: {user_input}")
                    
                if "shutdown" in user_input.lower() or "power down" in user_input.lower():
                    voice.speak("Powering down. Goodbye.")
                    sys.exit(0)

                # --- 3. GROQ INTENT PROCESSING ---
                logger.info("Groq is analyzing...")
                recent_history = memory.get_context_string(limit=2)
                
                system_prompt = """You are S.P.A.R.K., a highly intelligent AI assistant created by Sooraj. Be concise and professional.
You control the computer. Tools available: open_website(site_name), get_time(), open_application(app_name).
If the user asks you to use a tool, output ONLY JSON. Example: {"tool": "open_website", "arg": "google"}
Otherwise, just respond normally."""

                # Groq API Call formatting
                messages = [
                    {"role": "system", "content": system_prompt}
                ]
                
                # Add context safely
                if recent_history:
                    messages.append({"role": "system", "content": f"Previous context:\n{recent_history}"})
                    
                messages.append({"role": "user", "content": user_input})

                try:
                    # Using Llama 3 8B - Ultra fast and free
                    completion = groq_client.chat.completions.create(
                        model="llama3-8b-8192",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=150,
                    )
                    
                    answer = completion.choices[0].message.content.strip()
                    
                    # 4. JSON INTERCEPTOR
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
                            
                    # 5. NORMAL CONVERSATION
                    memory.remember("User", user_input)
                    memory.remember("S.P.A.R.K.", answer)
                    voice.speak(answer)
                    
                except Exception as e:
                    logger.error(f"Groq API Error: {e}")
                    voice.speak("I encountered a cognitive error reaching the cloud.")

    except KeyboardInterrupt: sys.exit(0)

if __name__ == "__main__":
    main()
