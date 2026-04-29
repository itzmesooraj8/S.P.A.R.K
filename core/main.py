from __future__ import annotations

import os
import re
from pathlib import Path

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


def generate_reply(model: Llama, user_input: str) -> str:
    messages = [
        {"role": "system", "content": "You are S.P.A.R.K., a concise offline assistant. Keep replies short and direct."},
        {"role": "user", "content": user_input},
    ]
    response = model.create_chat_completion(messages=messages, max_tokens=120, temperature=0.2)
    return response["choices"][0]["message"]["content"].strip()


def generate_reply_with_context(model: Llama, user_input: str, recent_history: str) -> str:
    prompt = (
        "System: You are S.P.A.R.K., a helpful AI assistant. Be concise and conversational.\n"
        f"{recent_history}"
        f"User: {user_input}\n"
        "S.P.A.R.K.:"
    )
    response = model(prompt, max_tokens=100, stop=["User:"])
    return response["choices"][0]["text"].strip()


def handle_tool_commands(tools: SparkTools, user_input: str) -> str | None:
    text = user_input.strip().lower()
    if not text:
        return None
    if "shutdown" in text:
        return tools.shutdown_pc()
    if "battery" in text:
        return tools.check_battery()
    if "what time" in text or "current time" in text:
        return tools.get_time()

    browser_match = re.search(r"open (?:browser )?(https?://\S+|www\.\S+|\S+\.com|\S+\.org)", text)
    if browser_match:
        target = browser_match.group(1)
        if not target.startswith(("http://", "https://")):
            target = f"https://{target}"
        return tools.open_browser(target)

    if text.startswith("open "):
        target = text.removeprefix("open ").strip()
        if target in {"youtube", "google", "github", "chatgpt"}:
            return tools.open_website(target)
        return tools.open_application(target)

    return None


def main() -> None:
    print("Loading local model. This is CPU-only by design.")
    tools = SparkTools()
    model = load_model()
    memory = SparkMemory()
    input_mode = os.getenv("SPARK_INPUT_MODE", "text").lower()
    ears = SparkEars() if input_mode == "voice" else None
    voice = SparkVoice() if input_mode == "voice" else None

    print("S.P.A.R.K. V1 Online. Type a prompt, or enter 'exit' to quit.")
    if voice:
        voice.speak("S.P.A.R.K. systems online. Memory core engaged.")

    while True:
        if ears:
            user_input = ears.listen()
            if not user_input:
                continue
        else:
            user_input = input("You> ").strip()
        if user_input.lower() in {"exit", "quit"}:
            if voice:
                voice.speak("S.P.A.R.K. powering down.")
            else:
                print("S.P.A.R.K. powering down.")
            break

        tool_response = handle_tool_commands(tools, user_input)
        if tool_response is not None:
            memory.remember("User", user_input)
            memory.remember("S.P.A.R.K.", tool_response)
            print(f"SPARK> {tool_response}")
            if voice:
                voice.speak(tool_response)
            continue

        print("S.P.A.R.K. is thinking...")
        try:
            recent_history = memory.get_context_string(limit=4)
            answer = generate_reply_with_context(model, user_input, recent_history)
            memory.remember("User", user_input)
            memory.remember("S.P.A.R.K.", answer)
            print(f"SPARK> {answer}")
            if voice:
                voice.speak(answer)
        except Exception as exc:
            print(f"[LLM Error]: {exc}")
            if voice:
                voice.speak("I encountered an error processing your request.")


if __name__ == "__main__":
    main()
