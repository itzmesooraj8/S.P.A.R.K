import json
import logging
import os
import sys
import warnings
from pathlib import Path
from typing import Any, Dict

import keyboard
from llama_cpp import Llama

from audio.stt import SparkEars
from audio.tts import SparkVoice
from core.memory import SparkMemory
from core.tools import SparkTools

warnings.filterwarnings("ignore")

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
    """
    Parse the LLM's JSON and trigger the physical system tool.

    Args:
        command_json: Parsed JSON command from the LLM.
        tools: SparkTools instance for command execution.
        voice: SparkVoice instance for audio feedback.

    Returns:
        Response string from the executed tool.
    """
    tool_name = command_json.get("tool")
    arg = command_json.get("arg", "")

    logger.info(f"Executing Tool: {tool_name} with args: '{arg}'")

    try:
        if tool_name == "open_website":
            response = tools.open_website(arg)
        elif tool_name == "get_time":
            response = tools.get_time()
        elif tool_name == "open_application":
            response = tools.open_application(arg)
        else:
            response = "I recognized a command, but the tool is not configured."
            logger.warning(f"Unrecognized tool requested: {tool_name}")

        voice.speak(response)
        return response
    except Exception as exc:
        logger.error(f"Tool execution failed: {exc}", exc_info=True)
        error_msg = "I encountered a system error while executing the tool."
        voice.speak(error_msg)
        return error_msg


def main() -> None:
    """Main event loop for S.P.A.R.K. Core."""
    logger.info("Initializing S.P.A.R.K. Subsystems...")

    try:
        llm = load_model()
        ears = SparkEars()
        voice = SparkVoice()
        tools = SparkTools()
        memory = SparkMemory()
    except Exception as exc:
        logger.critical(f"FATAL: Subsystem initialization failed. {exc}")
        sys.exit(1)

    voice.speak("S.P.A.R.K. initialized. Press F9 to wake me.")

    is_awake = False  # NEW: Tracks if we are in conversation mode

    try:
        while True:
            if not is_awake:
                # 1. ZERO-CPU IDLE STATE
                logger.info("System idling. Awaiting F9 hotkey trigger.")
                keyboard.wait("f9")
                is_awake = True

                # Flush the memory from the last session so it starts fresh
                memory.cursor.execute('DELETE FROM conversation')
                memory.conn.commit()

                voice.speak("Yes, sir? I am listening.")

            # The Ears will now listen silently in RAM. No print spam.
            user_input = ears.listen()

            if not user_input:
                continue  # Loop back instantly without logging

            logger.info(f"User Input: {user_input}")

            if "go to sleep" in user_input.lower() or "standby" in user_input.lower():
                voice.speak("Entering standby mode.")
                is_awake = False  # Put system back to sleep
                continue

            if "shutdown" in user_input.lower() or "power down" in user_input.lower():
                voice.speak("Powering down systems. Goodbye.")
                break

            # 3. SMART JSON THINKING
            logger.info("Analyzing intent via LLM...")
            recent_history = memory.get_context_string(limit=2)

            # [THE FIX] Clean, minimal prompt for Gemma-3 4B
            prompt = f"""System: You are S.P.A.R.K., a highly intelligent AI assistant created by Sooraj. Be concise, polite, and helpful.

You have access to the following tools:
- open_website (args: site_name)
- get_time (args: none)
- open_application (args: app_name)

If the user explicitly asks you to open a website, check the time, or launch an app, you MUST output ONLY valid JSON like this: {{"tool": "open_website", "arg": "youtube"}}
Otherwise, just respond normally to the user's text.

{recent_history}
User: {user_input}
S.P.A.R.K.:"""

            try:
                response = llm(prompt, max_tokens=100, stop=["User:"])
                answer = response["choices"][0]["text"].strip()

                # 4. JSON INTERCEPTOR
                if "{" in answer and "}" in answer:
                    try:
                        start = answer.find("{")
                        end = answer.rfind("}") + 1
                        command_json = json.loads(answer[start:end])
                        tool_result = execute_tool(command_json, tools, voice)
                        memory.remember("User", user_input)
                        memory.remember("S.P.A.R.K.", f"[Action Executed] {tool_result}")
                        continue
                    except json.JSONDecodeError:
                        pass

                # 5. NORMAL CONVERSATION
                memory.remember("User", user_input)
                memory.remember("S.P.A.R.K.", answer)
                voice.speak(answer)  # S.P.A.R.K speaks, then immediately listens again.

            except Exception as exc:
                logger.error(f"LLM processing error: {exc}")
                voice.speak("I encountered an error.")

    except KeyboardInterrupt:
        pass
    finally:
        sys.exit(0)


if __name__ == "__main__":
    main()
