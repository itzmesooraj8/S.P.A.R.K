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

    voice.speak("S.P.A.R.K. background mode activated. Press F9 to wake me.")
    logger.info("System idling. Awaiting F9 hotkey trigger.")

    try:
        while True:
            # 1. ZERO-CPU IDLE STATE
            keyboard.wait("f9")
            logger.info("Wake word triggered (F9). Transitioning to Active State.")

            voice.speak("Yes, sir?")

            # 2. LISTEN
            user_input = ears.listen()
            if not user_input:
                logger.debug("No voice input detected. Returning to idle.")
                continue

            logger.info(f"User Input: {user_input}")

            if "shutdown" in user_input.lower() or "power down" in user_input.lower():
                voice.speak("Powering down systems. Goodbye.")
                logger.info("Shutdown command received. Terminating process.")
                break

            # 3. SMART JSON THINKING
            logger.info("Analyzing intent via LLM...")
            recent_history = memory.get_context_string(limit=2)

            prompt = f"""System: You are S.P.A.R.K., an AI assistant. 
You have access to the following tools:
- open_website (args: site_name)
- get_time (args: none)
- open_application (args: app_name)

If the user wants you to perform an action, you MUST output ONLY a valid JSON block like this: {{"tool": "open_website", "arg": "youtube"}}
If no action is needed, simply reply normally and concisely.

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
                        logger.warning("LLM attempted to trigger a tool, but JSON was malformed.")

                # 5. NORMAL CONVERSATION
                logger.info("Executing standard conversational reply.")
                memory.remember("User", user_input)
                memory.remember("S.P.A.R.K.", answer)
                voice.speak(answer)

            except Exception as exc:
                logger.error(f"LLM processing error: {exc}")
                voice.speak("I encountered an error processing that request.")

    except KeyboardInterrupt:
        logger.info("Manual interrupt detected (Ctrl+C). Initiating graceful shutdown.")
    finally:
        logger.info("S.P.A.R.K. Core offline.")
        sys.exit(0)


if __name__ == "__main__":
    main()
