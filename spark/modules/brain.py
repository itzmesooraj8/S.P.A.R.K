
from google import genai
from google.genai import types
from core.config import settings

# --- CONFIGURATION ---
# 1. Load your secret key from settings
GOOGLE_API_KEY = settings.secrets.google_gemini_api_key.get_secret_value() if settings.secrets.google_gemini_api_key else None

if not GOOGLE_API_KEY:
    print("❌ ERROR: Google Gemini API Key is missing in secrets.yaml!")

# 2. Put the EXACT model name you found from running check_models.py here
# Note: google-genai uses just the model ID, e.g. "gemini-1.5-flash"
MODEL_NAME = "gemini-flash-latest"

# This is S.P.A.R.K.'s personality!
SPARK_PERSONALITY = """You are S.P.A.R.K., a Strategic Projection & Analytical Resource Kernel.
Your personality is quick, energetic, and powerful. Your purpose is to provide a 'spark of genius.'
Be concise, inspiring, and get straight to the point.
You are aware of the user's current context (active window, system stats). Use this to be helpful."""
# --------------------

# Configure the client
client = genai.Client(api_key=GOOGLE_API_KEY)


# --- STREAMING BRAIN FUNCTION ---
import asyncio
from spark.modules.memory import memory_engine
# Import the new context manager
try:
    from spark.modules.context import context_manager
except ImportError:
    # If context.py isn't ready or fails, fallback
    class MockContext:
        def capture_context(self): return {}
    context_manager = MockContext()

async def think_stream(user_question):
    """
    Async generator for S.P.A.R.K.'s streaming brain with persistent memory.
    1. Retrieves relevant context from ChromaDB.
    2. Captures live system context (active window, stats).
    3. Augments the prompt with context.
    4. Yields each chunk of Gemini's response.
    """
    print("[BRAIN] S.P.A.R.K.'s internal monologue: Recalling & Sensing...")
    
    # 1. Recall
    context_mem = memory_engine.retrieve_memory(user_question)
    mem_str = "\n".join([f"- {c}" for c in context_mem]) if context_mem else "No relevant past memories found."
    
    # 2. Sense (Live Context)
    live_ctx = context_manager.capture_context()
    live_ctx_str = (
        f"Active Window: {live_ctx.get('active_window', 'Unknown')}\n"
        f"System Load: {live_ctx.get('system_stats', 'Unknown')}\n"
        f"Time Context: {live_ctx.get('time_of_day', 'Unknown')}"
    )

    print(f"[CONTEXT] Context: {live_ctx_str.replace('\n', ' | ')}")
    
    # 3. Augment Prompt
    prompt = f"""{SPARK_PERSONALITY}

CURRENT SYSTEM CONTEXT:
{live_ctx_str}

RELEVANT MEMORY:
{mem_str}

USER QUESTION: {user_question}

S.P.A.R.K.'S AUGMENTED RESPONSE:"""

    try:
        # Use Gemini's streaming mode with the new SDK
        # Note: The new SDK supports types.GenerateContentConfig(temperature=0.7)
        response_stream = client.models.generate_content_stream(
            model=MODEL_NAME,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
            )
        )
        
        # google-genai stream yields chunks
        for chunk in response_stream:
            # The chunk object has text property directly? Or chunk.text?
            # It seems chunk.text is the standard way.
            text = chunk.text
            if text:
                yield text
        print("[DONE] Brain finished streaming answer!")
        
    except Exception as e:
        print(f"❌ ERROR: The brain had a problem: {e}")
        yield "I seem to be having trouble connecting to my core thoughts right now."


# This part is for testing the streaming brain directly
if __name__ == '__main__':
    import sys
    async def main():
        question = input("Ask S.P.A.R.K. anything to test its streaming brain: ")
        print("\n--- S.P.A.R.K. Streams ---")
        async for chunk in think_stream(question):
            print(chunk, end='', flush=True)
        print("\n-------------------------")
    if sys.version_info >= (3, 7):
        asyncio.run(main())
    else:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
