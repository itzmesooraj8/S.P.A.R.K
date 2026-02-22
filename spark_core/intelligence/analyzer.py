import json
import logging
from sandbox.docker_env import DockerEnvironment

async def run_flake8(sandbox: DockerEnvironment) -> int:
    result = await sandbox.run_command("flake8 .")
    if result.exit_code == 0:
        return 0
    return len(result.stdout.strip().splitlines())

async def run_mypy(sandbox: DockerEnvironment) -> int:
    result = await sandbox.run_command("mypy .")
    if result.exit_code == 0:
        return 0
    return len(result.stdout.strip().splitlines())

async def run_bandit(sandbox: DockerEnvironment) -> int:
    result = await sandbox.run_command("bandit -r . -f json")
    if result.exit_code != 0 and result.stdout:
        try:
            data = json.loads(result.stdout)
            return len(data.get("results", []))
        except Exception as e:
            logging.error(f"Failed to parse bandit output: {e}")
            return 1 # Fallback to 1 if we know it failed but can't parse
    return 0

async def run_complexity(sandbox: DockerEnvironment) -> float:
    result = await sandbox.run_command("radon cc . -s -a")
    if result.exit_code == 0 and result.stdout:
        # Tries to parse the average complexity from the output
        for line in result.stdout.splitlines():
            if "Average complexity:" in line:
                try:
                    parts = line.split()
                    return float(parts[-2]) # Expected format: "Average complexity: X.XX (A)"
                except Exception:
                    break
    return 0.0
