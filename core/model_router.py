# core/model_router.py
"""Model routing mapping matrix for S.P.A.R.K."""
import os
import logging

logger = logging.getLogger("spark.model_router")

# Valid, stable Groq models whitelisted for routing
GROQ_MODELS = {
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "gemma2-9b-it",
    "mixtral-8x7b-32768"
}

# Valid stable Ollama models whitelisted for fallback
OLLAMA_MODELS = {
    "gemma2:9b",
    "qwen2.5:7b",
    "qwen2.5:1.5b",
    "qwen2.5:0.5b",
    "gemma4" # Keep local config tag compatible
}


def get_groq_model() -> str:
    """Returns a validated Groq model name from environment or fallback."""
    preferred = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile").strip()
    if preferred in GROQ_MODELS:
        return preferred
        
    # Check if preferred matches a prefix
    for m in GROQ_MODELS:
        if preferred.startswith(m) or m.startswith(preferred):
            return m
            
    logger.warning(f"Preferred Groq model '{preferred}' is not whitelisted. Falling back to llama-3.3-70b-versatile.")
    return "llama-3.3-70b-versatile"


def get_ollama_model(configured_model: str | None = None) -> str:
    """Returns a validated Ollama model name."""
    preferred = (configured_model or os.getenv("OLLAMA_MODEL", "qwen2.5:7b")).strip()
    if preferred in OLLAMA_MODELS:
        return preferred
        
    # Standard fallback
    return "qwen2.5:7b"
