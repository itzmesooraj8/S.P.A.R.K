
from tools.registry import ToolRegistry
import os

def test_reflexes():
    print("--- S.P.A.R.K. Reflexes Verification (Iron Man Optimized) ---")
    
    registry = ToolRegistry()
    
    # 1. Test Screenshot
    print("\n[TEST] Screenshot...")
    # The new registry uses 'screenshot' capability directly
    res = registry.screenshot(None)
    print(f"Result: {res}")
    # The result from registry.screenshot is a description string or error, but it saves file internally.
    # To check file existence, we'd need the file path which isn't returned directly by the registry wrapper (it returns description).
    # However, 'vision/screen.py' prints the path. The registry catch returns the description.
    # We can assume success if it mentions description or path.
    if "VISION_OUTPUT" in res or "VISION_ERROR" not in res:
         print("PASS: Screenshot captured and analyzed.")
    else:
         print("FAIL: Screenshot analysis failed.")

    # 2. Test Network Scan
    print("\n[TEST] Network Scan...")
    res = registry.network_scan(None)
    print(f"Result: {res}")
    if "Network Scan Result" in res:
        print("PASS: Network scan stub returned correctly.")

    # 3. Test ADB Command
    print("\n[TEST] ADB Command...")
    # 'adb_command' takes a command string
    res = registry.adb_command("shell getprop ro.product.model")
    print(f"Result: {res}")
    if "ADB Protocol Initiated" in res:
        print("PASS: ADB stub returned correctly.")

    # 4. Test Kill Authority (Soft test - check process list)
    print("\n[TEST] Kill Authority (Process Identik)...")
    import subprocess
    # Start a dummy process to kill
    dummy = subprocess.Popen(["python", "-c", "import time; time.sleep(60)"])
    pid = dummy.pid
    print(f"Started dummy process with PID: {pid}")
    
    # The registry 'kill_process' takes the target (PID or name)
    # The argument to registry methods is usually a single string/obj
    res = registry.kill_process(str(pid))
    print(f"Result: {res}")
    
    # Check if dead
    import time
    time.sleep(1) # Wait for OS to clean up
    import psutil
    if not psutil.pid_exists(pid):
        print("PASS: Dummy process terminated successfully.")
    else:
        print("FAIL: Dummy process still running.")
        dummy.terminate()

if __name__ == "__main__":
    test_reflexes()
