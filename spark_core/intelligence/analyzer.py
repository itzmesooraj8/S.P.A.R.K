import json
import logging
from typing import Dict, Any
# from sandbox.docker_env import DockerEnvironment # Avoid circular import if possible, or use Any

async def run_flake8(sandbox: Any) -> Dict[str, Any]:
    """Runs flake8 and returns {count: int, status: str, error: str}"""
    cmd = "flake8 ."
    result = await sandbox.run_command(cmd)
    
    if result.exit_code == 0:
        return {"count": 0, "status": "success", "exit_code": 0}
        
    if result.exit_code in (127, -1) or "command not found" in result.stderr:
        return {"count": 0, "status": "missing", "error": "Tool not installed", "exit_code": result.exit_code}
        
    # Flake8 returns non-zero if issues found
    count = len(result.stdout.strip().splitlines())
    return {"count": count, "status": "success", "exit_code": result.exit_code}

async def run_mypy(sandbox: Any) -> Dict[str, Any]:
    """Runs mypy and returns {count: int, status: str, error: str}"""
    cmd = "mypy ."
    result = await sandbox.run_command(cmd)
    
    if result.exit_code == 0:
        return {"count": 0, "status": "success", "exit_code": 0}
        
    if result.exit_code in (127, -1) or "command not found" in result.stderr:
        return {"count": 0, "status": "missing", "error": "Tool not installed", "exit_code": result.exit_code}
        
    # Mypy returns non-zero if issues found
    # Filter for actual error lines (simplified)
    lines = [l for l in result.stdout.strip().splitlines() if "error:" in l]
    return {"count": len(lines), "status": "success", "exit_code": result.exit_code}

async def run_bandit(sandbox: Any) -> Dict[str, Any]:
    """Runs bandit and returns {count: int, status: str, error: str}"""
    cmd = "bandit -r . -f json"
    result = await sandbox.run_command(cmd)
    
    if result.exit_code in (127, -1) or "command not found" in result.stderr:
         return {"count": 0, "status": "missing", "error": "Tool not installed", "exit_code": result.exit_code}
         
    if result.stdout:
        try:
            data = json.loads(result.stdout)
            # Sum of distinct issues
            count = len(data.get("results", []))
            return {"count": count, "status": "success", "exit_code": result.exit_code}
        except Exception as e:
            return {"count": 0, "status": "error", "error": f"Parse error: {str(e)}", "exit_code": result.exit_code}
            
    return {"count": 0, "status": "unknown", "error": "No output", "exit_code": result.exit_code}

async def run_complexity(sandbox: Any) -> Dict[str, Any]:
    cmd = "radon cc . -s -a"
    result = await sandbox.run_command(cmd)
    
    score = 0.0
    if result.exit_code == 0 and result.stdout:
        for line in result.stdout.splitlines():
            if "Average complexity:" in line:
                try:
                    parts = line.split()
                    # Expected format: "Average complexity: A (X.XX)" or similar
                    # Actually radon output: "Average complexity: A (1.5)"
                    # Let's just grab the float
                    import re
                    match = re.search(r"\(([\d\.]+)\)", line)
                    if match:
                        score = float(match.group(1))
                except Exception:
                    pass
    
    status = "success" if result.exit_code == 0 else "error"
    return {"score": score, "status": status, "exit_code": result.exit_code}

