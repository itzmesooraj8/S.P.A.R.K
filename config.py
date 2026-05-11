import os
from dotenv import load_dotenv

load_dotenv()

LLM_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
LLM_BACKEND = "ollama"
VISION_MODEL = "gemma3:4b"
SPARK_HOST = os.getenv("SPARK_HOST", "0.0.0.0")
SPARK_PORT = int(os.getenv("SPARK_PORT", 8000))
SPARK_WORKSPACE_DIR = os.getenv("SPARK_WORKSPACE_DIR", os.getcwd())
SPARK_MODEL_PATH = os.getenv("SPARK_MODEL_PATH", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")
