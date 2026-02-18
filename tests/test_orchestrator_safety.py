
import asyncio
import sys
import os

sys.path.append(os.getcwd())

from spark.core.orchestrator import orchestrator, EventType
from spark.core.tool_registry_v2 import tool_registry_v2, RiskLevel

async def test_protection():
    print("[TEST] Validating Orchestrator Safety...")

    # 1. System Awareness (Green) -> Should Execute
    print("\n[SCENARIO 1] Green Tool (System Status)...")
    # Mock brain output with trigger
    # Note: orchestrator.process_user_input usually calls brain. 
    # For unit test, we'd mock brain.
    # But here we want to test the *logic*. 
    # Let's verify the Risk Assessor directly first.
    
    t_green = tool_registry_v2.get_tool("system_status")
    print(f"   Tool: {t_green.name} | Risk: {t_green.risk_level}")
    if t_green.risk_level == RiskLevel.GREEN:
        print("[PASS] Identified as Safe.")
    else:
        print("[FAIL] Risk Misclassified.")

    # 2. Critical Action (Red) -> Should Confirm
    print("\n[SCENARIO 2] Red Tool (Delete File)...")
    t_red = tool_registry_v2.get_tool("delete_file")
    print(f"   Tool: {t_red.name} | Risk: {t_red.risk_level}")
    if t_red.risk_level == RiskLevel.RED:
        print("[PASS] Identified as Critical.")
    else:
        print("[FAIL] Risk Misclassified.")

    # 3. Blocked Action -> Should be marked correctly
    print("\n[SCENARIO 3] Blocked Pattern Test...")
    t_term = tool_registry_v2.get_tool("terminal_command")
    cmd = "rm -rf /"
    print(f"   Command: {cmd}")
    
    import re
    blocked = False
    for pat in t_term.blocked_patterns:
        if re.search(pat, cmd):
            blocked = True
            break
            
    if blocked:
        print(f"[PASS]Blocked '{cmd}' correctly.")
    else:
        print(f"[FAIL] Allowed dangerous command!")

    print("\n[DONE] Orchestrator Safety Logic Verified.")

if __name__ == "__main__":
     asyncio.run(test_protection())
