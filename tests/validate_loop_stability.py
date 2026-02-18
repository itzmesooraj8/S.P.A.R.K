
import asyncio
import os
import sys
import psutil
import time
import random

# Ensure we can import from root
sys.path.append(os.getcwd())

from spark.modules.context import context_manager

class MockBrain:
    def __init__(self):
        self.iteration = 0
    
    async def think_stream(self, user_question):
        ctx = context_manager.capture_context()
        self.iteration += 1
        await asyncio.sleep(0.01) # Faster for testing
        yield "Thinking..."
        yield f" Context captured: {ctx.get('active_window')}"
        yield " Done."

async def stress_test_loop():
    print(f"[START] Stress Testing Core Loop (500 Iterations)...")
    
    process = psutil.Process()
    start_mem = process.memory_info().rss / 1024 / 1024
    print(f"Start Memory: {start_mem:.2f} MB")
    
    brain = MockBrain()
    errors = 0
    iterations = 500
    
    start_time = time.time()
    
    try:
        for i in range(iterations):
            try:
                user_input = f"Iteration {i}"
                response = ""
                async for chunk in brain.think_stream(user_input):
                    response += chunk
                
                if i % 100 == 0:
                    curr_mem = process.memory_info().rss / 1024 / 1024
                    print(f"Step {i}: Mem {curr_mem:.2f} MB")
                    sys.stdout.flush()
            
            except Exception as e:
                print(f"[X] Error at step {i}: {e}")
                errors += 1
                
    except KeyboardInterrupt:
        print("\n[STOP] User interrupted.")
        
    end_mem = process.memory_info().rss / 1024 / 1024
    print(f"\n[DONE] Test Complete.")
    print(f"Start Mem: {start_mem:.2f} MB")
    print(f"End Mem:   {end_mem:.2f} MB")
    print(f"Growth:    {end_mem - start_mem:.2f} MB")
    
    if errors == 0 and (end_mem - start_mem) < 50:
        print("RESULT: PASS (Stable)")
    else:
        print("RESULT: FAIL (Leaks or Errors)")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(stress_test_loop())
