import base64
import logging
from pathlib import Path

import httpx

from config import LLM_HOST, VISION_MODEL

logger = logging.getLogger("SPARK_VISION")

def describe_screen(screenshot_path: str, question: str) -> str:
    """Takes a screenshot path and a question, returns a visual description via Ollama."""
    try:
        with open(Path(screenshot_path), "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        response = httpx.post(
            f"{LLM_HOST}/api/chat",
            json={
                "model": VISION_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": question,
                        "images": [img_b64],
                    }
                ],
                "stream": False,
            },
            timeout=180.0,
        )
        response.raise_for_status()
        message = response.json().get("message", {})
        return str(message.get("content", "")).strip() or "I could not verify the screen visually, sir."
    except Exception as e:
        logger.error(f"Vision API Error: {e}")
        return f"I could not verify the screen visually, sir."
