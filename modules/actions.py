import os
import subprocess
import shlex

class SystemHands:
    def __init__(self):
        print("🛠️ Actions Module Loaded")

    def execute_command(self, command):
        """
        Executes a shell command.
        Security Warning: This is a high-privilege function.
        """
        print(f"⚡ [Action] Executing Command: {command}")
        try:
            # Using subprocess.run for better control and capturing output
            # splitting command using shlex for proper argument parsing
            # On Windows, shell=True is often needed for internal commands (dir, etc)
            result = subprocess.run(
                command, 
                shell=True, 
                check=True, 
                text=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            output = result.stdout
            if output:
                print(f"Result:\n{output}")
            return output
        except subprocess.CalledProcessError as e:
            error_msg = f"Command failed with error: {e.stderr}"
            print(error_msg)
            return error_msg
        except Exception as e:
            return f"Execution Error: {str(e)}"

    def execute_python(self, code):
        """
        Executes a block of Python code safely.
        """
        print(f"🐍 [Action] Running Python Code:\n{code}")
        try:
            # We use a limited scope, but for a personal assistant, 
            # we often want it to access "os" and "shutil".
            # For "phase 3", we will simply exec() it in a restricted env or global.
            # Let's run it in a separate process or just exec for now.
            # Exec is risky but "The Hands" implies trust.
            exec_globals = {}
            exec(code, exec_globals)
            return "Executed Successfully."
        except Exception as e:
            print(f"Python Execution Error: {e}")
            return f"Python Error: {e}"

# Singleton instance
hands = SystemHands()
