# core/model_router.py
"""Model routing mapping matrix for S.P.A.R.K."""
import os
import logging

logger = logging.getLogger("spark.model_router")

# Strict, predefined model dictionary containing stable cloud and offline models
MODEL_DICTIONARY = {
    "llama-3.3-70b-versatile": {"provider": "groq", "stable": True},
    "llama-3.1-8b-instant": {"provider": "groq", "stable": True},
    "gemma2-9b-it": {"provider": "groq", "stable": True},
    "mixtral-8x7b-32768": {"provider": "groq", "stable": True},
    "gemma2:9b": {"provider": "ollama", "stable": True},
    "qwen2.5:7b": {"provider": "ollama", "stable": True},
    "qwen2.5:1.5b": {"provider": "ollama", "stable": True},
    "qwen2.5:0.5b": {"provider": "ollama", "stable": True},
    "gemma4": {"provider": "ollama", "stable": True},
}

GROQ_MODELS = {k for k, v in MODEL_DICTIONARY.items() if v["provider"] == "groq" and v["stable"]}
OLLAMA_MODELS = {k for k, v in MODEL_DICTIONARY.items() if v["provider"] == "ollama" and v["stable"]}


def validate_model(model_name: str) -> bool:
    """Validate if the model name is in the strict predefined stable dictionary."""
    if not model_name:
        return False
    info = MODEL_DICTIONARY.get(model_name)
    return info is not None and info.get("stable", False)


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


def log_fallback_completion(model_used: str, completion: str) -> None:
    """Logs fallback completions inside structured, block-aligned console divider outlines."""
    width = 76
    print("\n┌" + "─" * (width - 2) + "┐")
    print(f"│ {'OLLAMA LOCAL FALLBACK COMPLETION':^{(width - 4)}} │")
    print(f"│ {'Model: ' + model_used:^{(width - 4)}} │")
    print("├" + "─" * (width - 2) + "┤")
    
    import textwrap
    wrapper = textwrap.TextWrapper(width=width - 4)
    lines = completion.split("\n")
    for raw_line in lines:
        if not raw_line.strip():
            print(f"│ {' ' * (width - 4)} │")
            continue
        for wrapped_line in wrapper.wrap(raw_line):
            print(f"│ {wrapped_line:<{width - 4}} │")
            
    print("└" + "─" * (width - 2) + "┘\n")
