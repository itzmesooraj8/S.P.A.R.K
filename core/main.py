from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import keyboard
from llama_cpp import Llama

from audio.stt import SparkEars
from audio.tts import SparkVoice
from core.memory import SparkMemory
from core.tools import SparkTools

MODEL_NAME = os.getenv("SPARK_MODEL_NAME", "Llama-3.2-3B-Instruct-Q4_K_M.gguf")
MODEL_PATH = Path(os.getenv("SPARK_MODEL_PATH", Path(__file__).resolve().parents[1] / MODEL_NAME))


def load_model() -> Llama:
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Model file not found: {MODEL_PATH}")
    return Llama(
        model_path=str(MODEL_PATH),
        n_ctx=int(os.getenv("SPARK_CTX", "2048")),
        n_threads=max(1, os.cpu_count() or 1),
        n_gpu_layers=0,
        verbose=False,
    )


def execute_tool(command_json, tools, voice):
    """Parses the LLM's JSON and triggers the physical tool."""
    tool_name = command_json.get("tool")
    arg = command_json.get("arg", "")

    if tool_name == "open_website":
        response = tools.open_website(arg)
    elif tool_name == "get_time":
        response = tools.get_time()
    elif tool_name == "open_application":
        response = tools.open_application(arg)
    else:
        response = "I recognized a command, but the tool is not configured."

    voice.speak(response)
    return response


def generate_reply_with_context(model: Llama, user_input: str, recent_history: str) -> str:
    prompt = (
        "System: You are S.P.A.R.K., an AI assistant. "
        "You have access to the following tools:\n"
        "- open_website (args: site_name)\n"
        "- get_time (args: none)\n"
        "- open_application (args: app_name)\n\n"
        "If the user wants you to perform an action, you MUST output ONLY a valid JSON block like this: {\"tool\": \"open_website\", \"arg\": \"youtube\"}\n"
        "If no action is needed, simply reply normally and concisely.\n\n"
        f"{recent_history}"
        f"User: {user_input}\n"
        "S.P.A.R.K.:"
    )
    response = model(prompt, max_tokens=100, stop=["User:"])
    return response["choices"][0]["text"].strip()


def main() -> None:
    llm = None
    ears = SparkEars()
    voice = SparkVoice()
    tools = SparkTools()
    memory = SparkMemory()

    voice.speak("S.P.A.R.K. background mode activated. Press F9 to wake me.")

    while True:
        print("\n[IDLE] Waiting for F9 hotkey...")
        keyboard.wait("f9")
        voice.speak("Yes, sir?")

        if llm is None:
            print("S.P.A.R.K. is loading the local model...")
            llm = load_model()

        user_input = ears.listen()
        if not user_input:
            continue

        if "shutdown" in user_input.lower() or "power down" in user_input.lower():
            voice.speak("Powering down systems. Goodbye.")
            break

        print("S.P.A.R.K. is analyzing intent...")
        recent_history = memory.get_context_string(limit=2)

        try:
            answer = generate_reply_with_context(llm, user_input, recent_history)

            if "{" in answer and "}" in answer:
                try:
                    start = answer.find("{")
                    end = answer.rfind("}") + 1
                    command_json = json.loads(answer[start:end])

                    print(f"[ROUTER] Decoded Command: {command_json}")
                    tool_result = execute_tool(command_json, tools, voice)

                    memory.remember("User", user_input)
                    memory.remember("S.P.A.R.K.", f"[Action Executed] {tool_result}")
                    continue

                except json.JSONDecodeError:
                    print("[ROUTER] Failed to parse LLM JSON.")

            memory.remember("User", user_input)
            memory.remember("S.P.A.R.K.", answer)
            voice.speak(answer)

        except Exception as exc:
            print(f"System Error: {exc}")
            voice.speak("I encountered an error processing that request.")


if __name__ == "__main__":
    main()
