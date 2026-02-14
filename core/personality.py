import google.generativeai as genai
import os
import asyncio
from dotenv import load_dotenv
from spark.modules.memory import memory_engine

# --- CONFIGURATION ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")
MODEL_NAME = "models/gemini-pro-latest"

SPARK_PERSONALITY = """You are S.P.A.R.K., a Strategic Projection & Analytical Resource Kernel.
Your personality is quick, energetic, and powerful. Your purpose is to provide a 'spark of genius.'
You have persistent memory, a secure vault for credentials, and control over your environment via MQTT.
Be concise, inspiring, and get straight to the point."""

# Configure Gemini
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel(MODEL_NAME)
else:
    model = None

async def think_stream(user_question):
    """
    Async generator for S.P.A.R.K.'s streaming brain with persistent memory.
    """
    if not model:
        yield "My core brain (Gemini) is not configured. Please set GOOGLE_GEMINI_API_KEY."
        return

    print("🧠 S.P.A.R.K.'s internal monologue: Recalling...")
    
    # 1. Recall from ChromaDB
    context = memory_engine.retrieve_memory(user_question)
    context_str = "\n".join([f"- {c}" for c in context]) if context else "No relevant past memories found."
    
    print("🧠 S.P.A.R.K.'s brain is thinking (augmented thinking)...")
    
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
        print("✅ Brain finished streaming answer!")
    except Exception as e:
        print(f"❌ ERROR: The brain had a problem: {e}")
        yield "I seem to be having trouble connecting to my core thoughts right now."

if __name__ == '__main__':
    async def test():
        async for chunk in think_stream("Hello"):
            print(chunk, end='', flush=True)
    asyncio.run(test())
