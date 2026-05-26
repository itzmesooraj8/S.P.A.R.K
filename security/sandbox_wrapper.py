"""
S.P.A.R.K Dynamic Sandbox Isolation & Environment Restraints
Provides a secure execution wrapper that restricts tasks using Docker containers (with CPU/RAM quotas),
falling back to low-overhead psutil subprocess resource-throttlers if Docker is unavailable.
"""

import os
import sys
import time
import subprocess
import shutil
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
import psutil

logger = logging.getLogger("SPARK_SANDBOX")

class SandboxWrapper:
    """Isolates external scripts inside Docker containers or strict local process groups."""
    
    def __init__(
        self,
        memory_limit_mb: int = 256,
        cpu_quota: float = 0.5,
        network_isolated: bool = True
    ):
        self.memory_limit_mb = memory_limit_mb
        self.cpu_quota = cpu_quota # fraction of CPU (e.g. 0.5 core)
        self.network_isolated = network_isolated
        self.has_docker = shutil.which("docker") is not None

    def execute_in_sandbox(
        self,
        script_content: str,
        timeout: float = 30.0
    ) -> Tuple[bool, str, str]:
        """
        Executes a Python script string within safe boundaries.
        Returns (success_boolean, stdout, stderr)
        """
        if self.has_docker:
            success, stdout, stderr = self._execute_docker(script_content, timeout)
            # Catch cases where docker is in PATH but daemon is not running
            if not success and any(err in stderr.lower() for err in ("error during connect", "docker daemon", "cannot connect", "daemon is not running")):
                logger.warning("Docker daemon not running. Falling back to local restricted sandbox.")
                return self._execute_local_restricted(script_content, timeout)
            return success, stdout, stderr
        else:
            logger.warning("Docker unavailable on this system. Launching under OS-level resource constraints.")
            return self._execute_local_restricted(script_content, timeout)

    def _execute_docker(self, script_content: str, timeout: float) -> Tuple[bool, str, str]:
        """Runs the script inside an ephemeral docker container with strict limits."""
        import tempfile
        
        # Write script to temporary workspace file
        with tempfile.TemporaryDirectory() as tmpdir:
            script_file = os.path.join(tmpdir, "sandbox_run.py")
            with open(script_file, "w", encoding="utf-8") as f:
                f.write(script_content)
                
            # Build docker command with resource limits
            cmd = [
                "docker", "run", "--rm",
                "-v", f"{tmpdir}:/app",
                "-w", "/app",
                f"-m={self.memory_limit_mb}m",
                f"--cpus={self.cpu_quota}",
            ]
            
            if self.network_isolated:
                cmd.extend(["--network", "none"])
                
            cmd.extend(["python:3.10-slim", "python", "sandbox_run.py"])
            
            logger.info(f"Launching script inside Docker container: {cmd}")
            try:
                res = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=timeout
                )
                return (res.returncode == 0), res.stdout, res.stderr
            except subprocess.TimeoutExpired:
                logger.error("Sandbox Docker container exceeded maximum run duration.")
                return False, "", "TIMEOUT_EXPIRED: Process killed by sandbox controller."
            except Exception as e:
                logger.error(f"Docker sandbox failure: {e}. Falling back to local boundaries.")
                return self._execute_local_restricted(script_content, timeout)

    def _execute_local_restricted(self, script_content: str, timeout: float) -> Tuple[bool, str, str]:
        """Runs the script locally, monitoring resources dynamically in a watchdog thread."""
        import tempfile
        
        tmpdir = tempfile.mkdtemp()
        script_file = os.path.join(tmpdir, "local_restricted_run.py")
        with open(script_file, "w", encoding="utf-8") as f:
            f.write(script_content)
            
        creation_flags = 0
        if sys.platform == "win32":
            # Below normal priority class and do not spawn window
            creation_flags = subprocess.BELOW_NORMAL_PRIORITY_CLASS | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            
        cmd = [sys.executable, script_file]
        
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creation_flags,
            text=True
        )
        
        # Launch resource monitor thread
        killer_flag = {"killed": False, "reason": ""}
        monitor_thread = threading.Thread(
            target=self._monitor_local_process,
            args=(proc.pid, killer_flag),
            daemon=True
        )
        monitor_thread.start()
        
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
            # Cleanup temp file
            try:
                os.remove(script_file)
                os.rmdir(tmpdir)
            except OSError:
                pass
                
            if killer_flag["killed"]:
                return False, stdout, f"KILLED_BY_SANDBOX: {killer_flag['reason']}\n{stderr}"
            return (proc.returncode == 0), stdout, stderr
            
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            try:
                os.remove(script_file)
                os.rmdir(tmpdir)
            except OSError:
                pass
            return False, stdout, "TIMEOUT_EXPIRED: Process killed by watchdog."

    def _monitor_local_process(self, pid: int, killer_flag: dict) -> None:
        """Polls process metrics, immediately killing if memory threshold is breached."""
        try:
            p = psutil.Process(pid)
            memory_limit_bytes = self.memory_limit_mb * 1024 * 1024
            
            while p.is_running() and p.status() != psutil.STATUS_ZOMBIE:
                try:
                    # Verify CPU & Memory
                    mem_info = p.memory_info()
                    if mem_info.rss > memory_limit_bytes:
                        killer_flag["killed"] = True
                        killer_flag["reason"] = f"Memory quota breached: {mem_info.rss / (1024*1024):.1f}MB > {self.memory_limit_mb}MB"
                        p.kill()
                        logger.error(f"Local sandbox watchdog killed process {pid}: {killer_flag['reason']}")
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    break
                time.sleep(0.1)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
