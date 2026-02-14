from tools.registry import ToolRegistry
import os

def test_phase_3_tools():
    registry = ToolRegistry()
    
    print("--- Testing Terminal Executor ---")
    # Should trigger permission
    is_tool, result = registry.parse_and_execute('[EXECUTE: run_terminal("echo Hello S.P.A.R.K.")]')
    print(f"Trigger Tool Result: {result}")
    
    if "PERMISSION_REQUIRED" in result:
        print("Permission requested as expected. Simulating Grant...")
        output = registry.execute_pending()
        print(f"Terminal Output: {output}")

    print("\n--- Testing File Manager (Write) ---")
    # Should trigger permission
    test_file = "phase3_test.txt"
    is_tool, result = registry.parse_and_execute(f'[EXECUTE: file_manager("write", "{test_file}", "Spark has hands now.")]')
    print(f"Trigger Tool Result: {result}")
    
    if "PERMISSION_REQUIRED" in result:
        print("Permission requested as expected. Simulating Grant...")
        output = registry.execute_pending()
        print(f"File Write Output: {output}")

    print("\n--- Testing File Manager (Read) ---")
    # Sensitive or not? In my implementation I didn't mark 'read' as sensitive explicitly in the code flow 
    # but the tool itself is in sensitive_tools list so ALL operations trigger permission currently.
    is_tool, result = registry.parse_and_execute(f'[EXECUTE: file_manager("read", "{test_file}")]')
    print(f"Trigger Tool Result: {result}")
    
    if "PERMISSION_REQUIRED" in result:
        print("Permission requested. Simulating Grant...")
        output = registry.execute_pending()
        print(f"File Content: {output}")

    print("\n--- Testing Path Validation ---")
    is_tool, result = registry.parse_and_execute('[EXECUTE: file_manager("list", "C:\\Windows")]')
    if "PERMISSION_REQUIRED" in result:
        output = registry.execute_pending()
        print(f"Validation Result (C:\\Windows): {output}")

    # Cleanup
    if os.path.exists(test_file):
        os.remove(test_file)

if __name__ == "__main__":
    test_phase_3_tools()
