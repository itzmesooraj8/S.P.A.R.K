import json
import logging
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict

warnings.filterwarnings("ignore")

from dotenv import load_dotenv
load_dotenv()

import keyboard
from llama_cpp import Llama

from audio.stt import SparkEars
from audio.tts import SparkVoice
from core.memory import SparkMemory
from core.tools import SparkTools

# ---------------------------------------------------------------------------
# ENTERPRISE LOGGING CONFIGURATION
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("SPARK_CORE")

MODEL_NAME = os.getenv("SPARK_MODEL_NAME", "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
MODEL_PATH = Path(os.getenv("SPARK_MODEL_PATH", Path(__file__).resolve().parents[1] / MODEL_NAME))


def load_model() -> Llama:
    """Load and initialize the local Llama model."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
    return Llama(
        model_path=str(MODEL_PATH),
        n_ctx=int(os.getenv("SPARK_CTX", "2048")),
        n_threads=max(1, os.cpu_count() or 1),
        n_gpu_layers=0,
        verbose=False,
    )


def execute_tool(command_json: Dict[str, Any], tools: SparkTools, voice: SparkVoice) -> str:
    """Parse the LLM's JSON and trigger the physical system tool."""
    tool_name = command_json.get("tool")
    arg = command_json.get("arg", "")
    logger.info(f"Executing Tool: {tool_name} | Args: {arg}")

    try:
        if tool_name == "open_website":
            response = tools.open_website(arg)
        elif tool_name == "get_time":
            response = tools.get_time()
        elif tool_name == "open_application":
            response = tools.open_application(arg)
        else:
            response = "Tool not configured."
        voice.speak(response)
        return response
    except Exception as e:
        logger.error(f"Tool Error: {e}")
        return "System error during tool execution."


def main():
    """Main event loop for S.P.A.R.K. Mark 4."""
    logger.info("Initializing S.P.A.R.K. Mark 4 Subsystems...")

    try:
        llm = load_model()
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
                    break  # Breaks the inner loop, goes back to F9 wait

                # If it's a hallucination (None), silently listen again
                if not user_input:
                    continue

                logger.info(f"User: {user_input}")

                if "shutdown" in user_input.lower() or "power down" in user_input.lower():
                    voice.speak("Powering down. Goodbye.")
                    sys.exit(0)

                # --- 3. GEMMA-3 INTENT PROCESSING ---
                logger.info("Gemma-3 is analyzing...")
                recent_history = memory.get_context_string(limit=2)

                # Clean, direct prompt for Gemma-3
                prompt = f"""System: You are S.P.A.R.K., a highly intelligent AI assistant created by Sooraj. Be concise and professional.
You control the computer. Tools available: open_website(site_name), get_time(), open_application(app_name).
If the user asks you to use a tool, output ONLY JSON. Example: {{"tool": "open_website", "arg": "google"}}

{recent_history}
User: {user_input}
S.P.A.R.K.:"""

                try:
                    response = llm(prompt, max_tokens=100, stop=["User:"])
                    answer = response['choices'][0]['text'].strip()

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
                    logger.error(f"LLM Error: {e}")
                    voice.speak("I encountered a cognitive error.")

    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
