
import sys
import os
import asyncio

# Ensure we can import from root
sys.path.append(os.getcwd())

from spark.modules.context import context_manager
from core.config import settings

def test_context_capture():
    print("\n--- Testing Context Manager ---")
    ctx = context_manager.capture_context()
    print(f"Active Window: {ctx.get('active_window')}")
    print(f"System Stats: {ctx.get('system_stats')}")
    print(f"Time Context: {ctx.get('time_of_day')}")
    
    if ctx.get('active_window') == "Unknown (pygetwindow not installed)":
        print("⚠️ WARNING: pygetwindow is not installed or failed. Context will be limited.")
    else:
        print("[OK] Context Manager seems to be working.")

async def test_brain_connection():
    print("\n--- Testing Brain Connection with New SDK ---")
    try:
        from spark.modules.brain import client, MODEL_NAME
        # Simple generation check
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents="Hello, do you see my context?"
        )
        print(f"[OK] Brain Responded: {response.text[:50]}...")
    except Exception as e:
        print(f"[X] Brain Connection Failed: {e}")
        try:
            print("Listing available models...")
            for model in client.models.list():
                if "gemini" in model.name:
                    print(f"- {model.name}")
        except Exception as list_e:
            print(f"Start listing failed: {list_e}")

if __name__ == "__main__":
    test_context_capture()
    asyncio.run(test_brain_connection())
