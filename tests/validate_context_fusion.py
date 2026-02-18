
import asyncio
import sys
import os

sys.path.append(os.getcwd())

from spark.modules.memory import memory_engine
from spark.modules.context import context_manager
from spark.modules.brain import think_stream

async def validate_fusion():
    print("[START] validating Context Fusion...")
    
    print("   [1] Injecting Memory...")
    test_code = "Project_Omega_99"
    memory_engine.add_memory(f"My secret project code is {test_code}")
    await asyncio.sleep(1)
    
    # Check context first to ensure it doesn't crash
    try:
        real_window = context_manager.get_active_window()
        print(f"   [2] Captured Window: {real_window}")
    except Exception as e:
        print(f"   [!] Context Failed: {e}")
        real_window = "Unknown"

    print("   [3] Asking Brain...")
    question = "What is my secret project code and what app am I using right now?"
    
    full_response = ""
    try:
        async for chunk in think_stream(question):
            full_response += chunk
            print(chunk, end='', flush=True)
        
        print("\n\n[ANALYSIS]")
        if test_code in full_response:
            print("[PASS] Method Recall")
        else:
            print("[FAIL] Memory Recall")
            
        print("[DONE]")
            
    except Exception as e:
        print(f"[CRITICAL FAIL] {e}")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(validate_fusion())
