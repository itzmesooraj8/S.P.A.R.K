import os
from dotenv import load_dotenv

load_dotenv()

LLM_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
LLM_MODEL = os.getenv("OLLAMA_MODEL", "gemma4")
LLM_BACKEND = os.getenv("LLM_BACKEND", "auto")
VISION_MODEL = "gemma3:4b"
SPARK_HOST = os.getenv("SPARK_HOST", "0.0.0.0")
SPARK_PORT = int(os.getenv("SPARK_PORT", 8000))
SPARK_WORKSPACE_DIR = os.getenv("SPARK_WORKSPACE_DIR", os.getcwd())
SPARK_MODEL_PATH = os.getenv("SPARK_MODEL_PATH", "")
LOG_LEVEL = os.getenv("LOG_LEVEL", "info")

# Groq token budgeting (auto-switch to Ollama at threshold)
GROQ_DAILY_TOKEN_LIMIT = int(os.getenv("GROQ_DAILY_TOKEN_LIMIT", "80000"))  # Switch to Ollama at 80k tokens
GROQ_TOKEN_LOG_FILE = os.getenv("GROQ_TOKEN_LOG_FILE", os.path.join(SPARK_WORKSPACE_DIR, "spark_dev_memory", "token_log.json"))
GROQ_COOLDOWN_SECONDS = int(os.getenv("SPARK_GROQ_COOLDOWN_SECONDS", "480"))  # 8 minutes
