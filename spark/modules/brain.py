
import google.generativeai as genai
import os
from dotenv import load_dotenv

# --- CONFIGURATION ---
# 1. Load your secret key from .env
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_GEMINI_API_KEY")

# 2. Put the EXACT model name you found from running check_models.py here
MODEL_NAME = "models/gemini-pro-latest"

# This is S.P.A.R.K.'s personality!
SPARK_PERSONALITY = """You are S.P.A.R.K., a Strategic Projection & Analytical Resource Kernel.\nYour personality is quick, energetic, and powerful. Your purpose is to provide a 'spark of genius.'\nBe concise, inspiring, and get straight to the point."""
# --------------------

# Configure the magic remote control
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel(MODEL_NAME)


# --- STREAMING BRAIN FUNCTION ---
import asyncio
from spark.modules.memory import memory_engine

async def think_stream(user_question):
    """
    Async generator for S.P.A.R.K.'s streaming brain with persistent memory.
    1. Retrieves relevant context from ChromaDB.
    2. Augments the prompt with context.
    3. Yields each chunk of Gemini's response.
    """
    print("🧠 S.P.A.R.K.'s internal monologue: Recalling...")
    
    # 1. Recall
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
        # Use Gemini's streaming mode
        response_stream = model.generate_content(prompt, stream=True)
        for chunk in response_stream:
            text = getattr(chunk, 'text', None)
            if text:
                yield text
        print("✅ Brain finished streaming answer!")
        
        # 3. Remember (The calling loop in app.py should store the full interaction)
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
