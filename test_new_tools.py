from tools.registry import ToolRegistry
import time
import subprocess
import os

def test_tools():
    registry = ToolRegistry()
    
    print("--- Testing Screen Scan ---")
    # This might fail if no display is available, but on a local machine it should work.
    # We'll see if it at least imports and runs the capture logic.
    result = registry.screen_scan(None)
    print(f"Screen Scan Result: {result}")

    print("\n--- Testing Task Killer ---")
    # Start a dummy process (notepad)
    print("Starting notepad...")
    p = subprocess.Popen(["notepad.exe"])
    time.sleep(2) # Wait for it to start
    
    print("Attempting to kill notepad...")
    result = registry.kill_process("notepad")
    print(f"Kill Result (fuzzy): {result}")
    
    # Verify it's gone
    import psutil
    is_running = any("notepad" in p.name().lower() for p in psutil.process_iter())
    print(f"Is notepad still running? {is_running}")

    print("\n--- Testing Safety Check ---")
    result = registry.kill_process("python.exe")
    print(f"Safety Check Result: {result}")

if __name__ == "__main__":
    test_tools()
