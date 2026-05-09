from __future__ import annotations

import os


LLM_BACKEND = os.getenv("LLM_BACKEND", "ollama")
LLM_HOST = os.getenv("LLM_HOST", "http://127.0.0.1:11434")
LLM_MODEL = os.getenv("LLM_MODEL", "mistral")
VISION_MODEL = os.getenv("VISION_MODEL", os.getenv("LLM_MODEL", "llama3.2-vision"))