
import asyncio
import sys
import os
import time

sys.path.append(os.getcwd())

# Import our Brain Manager
from spark.modules.brain_manager import brain_manager

# We need to monkeypatch the cloud function to control failure
import spark.modules.brain as cloud_module

# Control Flags
FORCE_CLOUD_FAIL = False

# Mock Cloud generator
async def mock_cloud_think_stream(prompt):
    if FORCE_CLOUD_FAIL:
        raise Exception("503 Service Unavailable (Mocked)")
    # Simulate slight network delay
    await asyncio.sleep(0.1)
    yield "Cloud Response: " + prompt

# Apply Monkeypatch - This now works because brain_manager uses `cloud_brain.think_stream`
cloud_module.think_stream = mock_cloud_think_stream

async def run_stress_test():
    global FORCE_CLOUD_FAIL
    print("[START] Full System Stress Test...")
    
    # 1. Normal Operation
    print("\n[TEST 1] Normal Operation (Cloud)...")
    try:
        response = ""
        async for chunk in brain_manager.think("Hello Cloud"):
            response += chunk
        if "Cloud Response" in response:
            print("[PASS] Cloud Response verified.")
        else:
            print(f"[FAIL] Unexpected response: {response}")
    except Exception as e:
        print(f"[FAIL] Cloud threw unexpected error: {e}")

    # 2. Forced Failure & Fallback
    print("\n[TEST 2] Forced Cloud Failure -> Local Fallback...")
    FORCE_CLOUD_FAIL = True
    
    # We need to trigger enough failures to trip circuit breaker (threshold=3)
    print("   Tripping Circuit Breaker (3 attempts)...")
    for i in range(3):
        try:
            print(f"   Attempt {i+1}...", end='', flush=True)
            response = ""
            async for chunk in brain_manager.think(f"Fail {i}"):
                response += chunk
            
            # Check if fallback happened
            if "Switched to Local Backup" in response:
               print(f" -> Success: Fallback triggered.")
            elif "Cloud Response" in response:
               print(f" -> [FAIL] Cloud succeeded (Should fail).")
        except Exception as e:
            print(f" -> [FAIL] Error caught: {e}")

    # Verify Circuit State
    if brain_manager.cloud_status == "UNSTABLE":
        print("[PASS] Circuit Breaker OPEN (Status: UNSTABLE)")
    else:
        print(f"[FAIL] Circuit Breaker status incorrect: {brain_manager.cloud_status}")

    # 3. Local Mode Persistence (While Open)
    print("\n[TEST 3] Persistence in Local Mode...")
    response = ""
    async for chunk in brain_manager.think("Still Local?"):
        response += chunk
    
    if "Switched to Local Backup" in response:
        print("[PASS] Correctly stayed in Local Mode.")
    else:
        print(f"[FAIL] Leaked back to Cloud? Response: {response}")

    # 4. Recovery (Cooldown)
    print("\n[TEST 4] Cooldown Recovery...")
    print("   Simulating 61s wait...")
    
    # Manually reset breaker state for test to simulate time passing (easier than patching time.time globally)
    # Patching brain_manager.last_failure_time directly
    brain_manager.last_failure_time = time.time() - 65
    
    FORCE_CLOUD_FAIL = False # Fix cloud
    
    response = ""
    async for chunk in brain_manager.think("Am I back?"):
        response += chunk
    
    if "Cloud Response" in response:
        print("[PASS] Successfully recovered to Cloud.")
    else:
        print(f"[FAIL] Still using Local? Response: {response}")

    # 5. Concurrency Stress
    print("\n[TEST 5] Rapid Fire Concurrency (5 Requests)...")
    tasks = []
    start_time = time.time()
    for i in range(5):
        tasks.append(asyncio.create_task(collect_response(f"Quick {i}")))
    
    # We wait for them
    results = await asyncio.gather(*tasks)
    duration = time.time() - start_time
    print(f"   Processed 5 requests in {duration:.2f}s")
    
    success_count = sum(1 for r in results if "Cloud Response" in r)
    if success_count == 5:
        print("[PASS] All concurrency requests handled correctly.")
    else:
        print(f"[FAIL] Only {success_count}/5 succeeded.")

    print("\n[DONE] Stress Test Complete.")

async def collect_response(prompt):
    res = ""
    async for chunk in brain_manager.think(prompt):
        res += chunk
    return res

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_stress_test())
