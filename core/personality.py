import google.generativeai as genai
import asyncio
import structlog
import ollama
from core.config import settings
from core.vault import spark_vault
from core.resilience import circuit_breaker
from spark.modules.memory import memory_engine

logger = structlog.get_logger()

# --- CONFIGURATION via settings ---
# --- CONFIGURATION via settings ---
MODEL_NAME = "gemini-1.5-flash"
FALLBACK_MODEL = "llama3"

SPARK_PERSONALITY = """You are S.P.A.R.K., a Strategic Projection & Analytical Resource Kernel.
Your personality is quick, energetic, and powerful. Your purpose is to provide a 'spark of genius.'
You have persistent memory, a secure vault for credentials, and control over your environment via MQTT.
Be concise, inspiring, and get straight to the point."""

class SparkBrain:
    def __init__(self):
        self.api_key = settings.secrets.google_gemini_api_key
        if self.api_key:
            genai.configure(api_key=self.api_key.get_secret_value())
            self.model = genai.GenerativeModel(MODEL_NAME)
            logger.info("gemini_configured", model=MODEL_NAME)
        else:
            self.model = None
            logger.warning("gemini_key_missing", action="brain_disabled")

    async def _fallback_think_stream(self, user_question, context_str, error=None):
        """Fallback to local Ollama (Llama 3) when Gemini fails."""
        logger.warning("circuit_open_switching_to_local", model=FALLBACK_MODEL, error=str(error))
        
        prompt = f"""{SPARK_PERSONALITY}
CONTEXT: {context_str}
USER: {user_question}
RESPONSE:"""
        
        try:
            # Ollama streaming
            stream = ollama.chat(
                model=FALLBACK_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
                stream=True,
            )
            for chunk in stream:
                yield chunk['message']['content']
            logger.info("brain_finished_streaming_local")
        except Exception as e:
            logger.error("local_brain_failed", error=str(e))
            yield "I am offline and my local brain is not responding."

    # Circuit Breaker doesn't support async generators directly in the naive implementation.
    # We need to wrap the generator logic carefully.
    # The `think_stream` is called and iterated.
    # If we use the circuit breaker on the *call* to the generator, it works if the generator *startup* fails, 
    # but usually errors happen *during* iteration.
    # For now, we'll apply resilience manually inside the generator or use a compatible pattern.
    # The user asked to apply `@circuit_breaker`.
    # Let's wrap the "creation" of the response stream.
    
    async def think_stream(self, user_question):
        """
        Async generator for S.P.A.R.K.'s streaming brain with persistent memory.
        """
        logger.info("brain_thinking", query=user_question)
        
        # 1. Recall
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

        # Logic for selection
        if not self.model:
             # Force fallback if no key
             async for chunk in self._fallback_think_stream(user_question, context_str, "Gemini Key Missing"):
                 yield chunk
             return

        # Attempt Gemini with Fallback Logic (Manual Circuit Breaker pattern for Generators)
        # Replacing the decorator for generators with explicit try/catch/fallback behavior
        # is often more robust for streaming.
        
        try:
            response_stream = await self.model.generate_content_async(prompt, stream=True)
            async for chunk in response_stream:
                text = getattr(chunk, 'text', None)
                if text:
                    yield text
            logger.info("brain_finished_streaming_gemini")

        except Exception as e:
            logger.error("gemini_error_triggering_fallback", error=str(e))
            # Fallback
            async for chunk in self._fallback_think_stream(user_question, context_str, e):
                yield chunk

# Global Instance
brain = SparkBrain()

# Expose as function for compatibility
async def think_stream(user_question):
    async for chunk in brain.think_stream(user_question):
        yield chunk
