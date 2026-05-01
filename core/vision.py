import base64
import os
import logging
from groq import Groq

logger = logging.getLogger("SPARK_VISION")

def describe_screen(screenshot_path: str, question: str) -> str:
    """Takes a screenshot path and a question, returns a visual description via Groq."""
    try:
        with open(screenshot_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            return "Vision error: Missing GROQ_API_KEY."

        client = Groq(api_key=api_key)
        
        # Using LLaVA or the currently active vision model on Groq
        response = client.chat.completions.create(
            model="llama-3.2-11b-vision-preview", # Fallback to llama-3.2-11b-vision-preview if llava fails, but let's try the modern Llama 3.2 Vision
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{img_b64}"}}
                ]
            }],
            max_tokens=200
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Vision API Error: {e}")
        return f"I could not verify the screen visually, sir."
