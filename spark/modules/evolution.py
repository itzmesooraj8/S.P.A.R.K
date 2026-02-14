import os
import re

class EvolutionEngine:
    def __init__(self, log_path="spark.log"):
        self.log_path = log_path
        self.common_errors = {
            "ConnectionRefusedError": "IoT Bridge connectivity issue",
            "ModuleNotFoundError": "Missing dependency in module",
            "FileNotFoundError": "File path incorrect or resource missing",
            "PermissionError": "System access restricted"
        }

    def scan_for_errors(self):
        """
        Scans the log file for known error patterns.
        """
        if not os.path.exists(self.log_path):
            print(f"[EVO] Log file {self.log_path} not found.")
            return []

        print(f"[EVO] Scanning {self.log_path} for system issues...")
        detected_issues = []
        
        try:
            with open(self.log_path, 'r') as f:
                # Read last 100 lines for efficiency
                lines = f.readlines()[-100:]
                
            for line in lines:
                for error, description in self.common_errors.items():
                    if error in line:
                        detected_issues.append({
                            "error": error,
                            "description": description,
                            "context": line.strip()
                        })
        except Exception as e:
            print(f"[EVO] Error reading logs: {e}")
            
        return detected_issues

    def draft_fix(self, issue):
        """
        Simulates using the LLM to draft a fix for a detected issue.
        """
        print(f"[EVO] Analyzing {issue['error']}...")
        
        # Mock fix logic
        fix_suggestion = f"""# PROPOSED FIX FOR: {issue['error']}
# Description: {issue['description']}
# Location identified from log: {issue['context']}

# Proposed modification in relevant module:
def try_reconnect():
    try:
        # Re-attempt connection logic
        pass
    except {issue['error']}:
        print("Retrying in 5 seconds...")
        time.sleep(5)
"""
        return fix_suggestion

    def propose_update(self, detected_issues):
        """
        Generates a summary of proposed updates for the user.
        """
        if not detected_issues:
            return "No critical system errors detected. S.P.A.R.K. is healthy."

        proposals = []
        for issue in detected_issues:
            fix = self.draft_fix(issue)
            proposals.append({
                "issue": issue['error'],
                "suggestion": fix
            })
            
        return proposals

# Global engine
evolution_engine = EvolutionEngine()

if __name__ == "__main__":
    # Test the evolution engine
    # Create a dummy log file with an error
    with open("spark.log", "w") as f:
        f.write("[2026-02-14 22:15:00] ERROR: iot_bridge.py - ConnectionRefusedError: [WinError 10061]\n")
        f.write("[2026-02-14 22:15:05] ERROR: iot_bridge.py - ConnectionRefusedError: [WinError 10061]\n")

    engine = EvolutionEngine()
    issues = engine.scan_for_errors()
    if issues:
        print(f"[EVO] Found {len(issues)} issues.")
        proposals = engine.propose_update(issues)
        for p in proposals:
            print(f"\n--- PROPOSAL FOR {p['issue']} ---")
            print(p['suggestion'])
    
    # Clean up dummy log (optional, or keep for audit)
    # os.remove("spark.log")
