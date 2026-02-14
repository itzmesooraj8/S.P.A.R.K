
from spark.modules.registry import spark_tools
import os

def test_reflexes():
    print("--- S.P.A.R.K. Reflexes Verification ---")
    
    # 1. Test Screenshot
    print("\n[TEST] Screenshot...")
    res = spark_tools.dispatch("screenshot")
    print(f"Result: {res}")
    if os.path.exists(res):
        print("PASS: Screenshot file created.")
        # Cleanup
        os.remove(res)
    else:
        print("FAIL: Screenshot file not found.")

    # 2. Test Network Scan
    print("\n[TEST] Network Scan...")
    res = spark_tools.dispatch("network_scan")
    print(f"Result: {res}")
    if "Network Scan Complete" in res:
        print("PASS: Network scan stub returned correctly.")

    # 3. Test ADB Command
    print("\n[TEST] ADB Command...")
    res = spark_tools.dispatch("adb_command", command="shell getprop ro.product.model")
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
    
    res = spark_tools.dispatch("kill_process", pid=pid)
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
