import google.generativeai as genai
import asyncio
import structlog
from core.config import settings
from core.vault import spark_vault
from spark.modules.memory import memory_engine

logger = structlog.get_logger()

# --- CONFIGURATION via settings ---
MODEL_NAME = "models/gemini-pro"  # Default generic name, specific version in settings?
# settings.vision.model is for vision, we need an LLM model setting.
# For now, we'll keep the constant or add it to settings later. 
# Using settings.secrets for key.

SPARK_PERSONALITY = """You are S.P.A.R.K., a Strategic Projection & Analytical Resource Kernel.
Your personality is quick, energetic, and powerful. Your purpose is to provide a 'spark of genius.'
You have persistent memory, a secure vault for credentials, and control over your environment via MQTT.
Be concise, inspiring, and get straight to the point."""

# Configure Gemini
api_key = settings.secrets.google_gemini_api_key
if api_key:
    genai.configure(api_key=api_key.get_secret_value())
    model = genai.GenerativeModel(MODEL_NAME)
    logger.info("gemini_configured", model=MODEL_NAME)
else:
    model = None
    logger.warning("gemini_key_missing", action="brain_disabled")

async def think_stream(user_question):
    """
    Async generator for S.P.A.R.K.'s streaming brain with persistent memory.
    """
    if not model:
        yield "My core brain (Gemini) is not configured. Please set GOOGLE_GEMINI_API_KEY in secrets.yaml or env."
        return

    logger.info("brain_thinking", query=user_question)
    
    # 1. Recall from ChromaDB
    try:
        context = memory_engine.retrieve_memory(user_question)
        context_str = "\n".join([f"- {c}" for c in context]) if context else "No relevant past memories found."
    except Exception as e:
        logger.error("memory_retrieval_failed", error=str(e))
        context_str = "Memory unavailable."
    
    # 2. Augment Prompt
    prompt = f"""{SPARK_PERSONALITY}

RELEVANT CONTEXT FROM MEMORY:
{context_str}

USER QUESTION: {user_question}

S.P.A.R.K.'S AUGMENTED RESPONSE:"""

    try:
        response_stream = model.generate_content(prompt, stream=True)
        for chunk in response_stream:
            text = getattr(chunk, 'text', None)
            if text:
                yield text
        logger.info("brain_finished_streaming")
        
        # 3. Store interaction in Memory (Self-learning)
        # We should ideally wait for the full response to be complete before storing.
        # This interaction loop is handled in the orchestrator usually, but we can log here.
        
    except Exception as e:
        logger.error("brain_error", error=str(e))
        yield "I seem to be having trouble connecting to my core thoughts right now."

# Vault Integration Helper
def store_memory(key, value):
    spark_vault.set_secret(key, value)
    logger.info("memory_stored_securely", key=key)

if __name__ == '__main__':
    async def test():
        async for chunk in think_stream("Hello"):
            print(chunk, end='', flush=True)
    asyncio.run(test())
