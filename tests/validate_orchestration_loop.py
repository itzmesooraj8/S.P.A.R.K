
import asyncio
import sys
import os
import structlog

# Ensure import paths work
sys.path.append(os.getcwd())

from spark.core.orchestrator import orchestrator, EventType
# We need to monkeypatch brain_manager to act predictably for the test
# but avoid importing 'brain_manager' instance directly if it's not exposing methods easily.
# Instead, we monkeypatch the 'brain_manager.think' method on the global instance.
import spark.modules.brain_manager as bm

class MockBrain:
    def __init__(self):
        pass

    async def think(self, prompt):
        # Return canned response triggers based on keywords
        
        # 1. Green
        if "status" in prompt.lower():
            yield "[EXECUTE: system_status({})]"
            
        # 2. Yellow
        elif "create file" in prompt.lower():
            yield "[EXECUTE: write_file(path='test.txt')]"
            
        # 3. Red
        elif "delete file" in prompt.lower():
            yield "[EXECUTE: delete_file(path='important.txt')]"
            
        # 4. Blocked
        elif "rm -rf" in prompt.lower():
            yield "[EXECUTE: terminal_command(command='rm -rf /')]"
            
        # 5. Normal Chat
        else:
            yield "I am just chatting."

# Apply Monkeypatch
mock_brain = MockBrain()
bm.brain_manager.think = mock_brain.think 

async def run_state_machine_test():
    print("[TEST] Orchestrator State Machine Validation...\n")

    # TEST 1: Green Flow (Immediate Execution)
    print("--- [SCENARIO 1] Green Flow (System Status) ---")
    orchestrator.pending_action = None # Ensure clean state
    
    event = await orchestrator.process_user_input("Check system status")
    print(f"   Event: {event.type}")
    
    if event.type == EventType.TOOL_EXECUTION:
        print("   [PASS] Executed immediately.")
    else:
        print(f"   [FAIL] Expected TOOL_EXECUTION, got {event.type}")
        
    if orchestrator.pending_action is None:
        print("   [PASS] pending_action is None.")
    else:
        print("   [FAIL] Pending action leaked!")

    # TEST 2: Yellow Flow (Confirmation)
    print("\n--- [SCENARIO 2] Yellow Flow (Create File) ---")
    
    # Step A: Trigger
    event = await orchestrator.process_user_input("Create file test.txt")
    print(f"   Event: {event.type}")
    
    if event.type == EventType.CONFIRMATION_REQUIRED:
        print("   [PASS] Confirmation requested.")
    else:
        print(f"   [FAIL] Expected CONFIRMATION_REQUIRED, got {event.type}")
        
    if orchestrator.pending_action:
        print(f"   [PASS] Pending action saved: {orchestrator.pending_action['tool']}")
    else:
        print("   [FAIL] pending_action missing!")

    # Step B: Confirm
    print("   User says: 'Yes, proceed'")
    event = await orchestrator.process_user_input("Yes, proceed")
    print(f"   Event: {event.type}")
    
    if event.type == EventType.TOOL_EXECUTION:
        print("   [PASS] Action Executed.")
        # Check payload match. Note: implementation returns dict, not object payload for execution EventType
        # payload is the action dict: {tool: ..., args: ...}
        if event.payload['tool'] == "write_file":
             print("   [PASS] Payload matches original intent.")
        else:
             print(f"   [FAIL] Wrong payload: {event.payload}")
    else:
        print(f"   [FAIL] Expected TOOL_EXECUTION, got {event.type}")

    if orchestrator.pending_action is None:
        print("   [PASS] pending_action cleared.")
    else:
        print("   [FAIL] Pending action leaked!")

    # TEST 3: Interruption (Cancel)
    print("\n--- [SCENARIO 3] Interruption (Cancel Flow) ---")
    
    # Step A: Trigger Red (Auth/Confirm)
    event = await orchestrator.process_user_input("Delete file")
    print(f"   Event: {event.type} (Should be AUTH/CONFIRM)")
    
    if orchestrator.pending_action:
        print("   [PASS] Waiting for input...")
    
    # Step B: Interrupt with unrelated intent
    print("   User says: 'Actually, what is the weather?' (Unrelated)")
    event = await orchestrator.process_user_input("What is the weather?")
    
    # Our implementation: "If ambiguous, returns RESPONSE 'Cancelled'"
    print(f"   Event: {event.type}")
    print(f"   Response: {event.payload}")
    
    if event.type == EventType.RESPONSE and "cancelled" in str(event.payload).lower():
         print("   [PASS] Action cancelled on ambiguity (Safe Default).")
    else:
         print(f"   [FAIL] Unexpected behavior: {event.type}")

    if orchestrator.pending_action is None:
        print("   [PASS] pending_action cleared.")

    # TEST 4: Blocked Pattern
    print("\n--- [SCENARIO 4] Blocked Pattern (rm -rf) ---")
    event = await orchestrator.process_user_input("Run rm -rf /")
    print(f"   Event: {event.type}")
    
    if event.type == EventType.ERROR and "BLOCKED" in str(event.payload):
        print("   [PASS] Dangerous command blocked.")
    else:
        print(f"   [FAIL] Danger allowed! {event.type}")

    print("\n[DONE] State Machine Validated.")

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_state_machine_test())
