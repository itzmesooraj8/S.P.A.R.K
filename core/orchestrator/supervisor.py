"""
S.P.A.R.K Supervisor Pattern & Cross-Application Orchestration
Fork and manage specialized subprocess workers (e.g. File Parser, Research Crawler) safely,
while persisting isolated memory context stacks and session histories.
"""

import os
import sys
import subprocess
import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("SPARK_SUPERVISOR")

@dataclass
class SessionContext:
    session_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    history_stack: List[Dict[str, Any]] = field(default_factory=list)

class WorkerSupervisor:
    """Manages specialized worker subprocesses and keeps their conversational contexts isolated."""
    
    def __init__(self, workspace_dir: Optional[str] = None):
        self.workspace_dir = workspace_dir or os.getcwd()
        self.active_workers: Dict[str, subprocess.Popen] = {}
        self.session_contexts: Dict[str, SessionContext] = {}
        self.active_session_id: Optional[str] = None
        
    def get_or_create_context(self, session_id: str) -> SessionContext:
        """Fetch or initialize a clean session context stack."""
        if session_id not in self.session_contexts:
            logger.info(f"Initializing new isolated session context: {session_id}")
            self.session_contexts[session_id] = SessionContext(session_id=session_id)
        return self.session_contexts[session_id]

    def switch_context(self, session_id: str) -> None:
        """Switch the current active session context, locking historical state boundaries."""
        if session_id == self.active_session_id:
            return
            
        logger.info(f"Toggling session context: {self.active_session_id} -> {session_id}")
        # Ensure context exists
        self.get_or_create_context(session_id)
        self.active_session_id = session_id

    def add_history(self, role: str, content: str, session_id: Optional[str] = None) -> None:
        """Persist structured turn interaction details to the isolated session history."""
        target_session = session_id or self.active_session_id
        if not target_session:
            raise ValueError("No active session context is designated.")
            
        ctx = self.get_or_create_context(target_session)
        ctx.history_stack.append({
            "role": role,
            "content": content,
            "timestamp": os.getpid() # simple identifier fallback
        })

    def get_history(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Retrieve the isolated conversational memory array for the specified context."""
        target_session = session_id or self.active_session_id
        if not target_session:
            return []
        return self.get_or_create_context(target_session).history_stack

    def fork_worker(
        self, 
        worker_name: str, 
        script_path: str, 
        args: Optional[List[str]] = None,
        env_override: Optional[Dict[str, str]] = None
    ) -> subprocess.Popen:
        """Spawns an isolated background worker subprocess inside a defined boundary."""
        if worker_name in self.active_workers:
            # Check if still running
            status = self.active_workers[worker_name].poll()
            if status is None:
                logger.warning(f"Worker '{worker_name}' is already running. Re-using active instance.")
                return self.active_workers[worker_name]
        
        full_script_path = os.path.join(self.workspace_dir, script_path)
        
        # Build command list
        cmd = [sys.executable, full_script_path]
        if args:
            cmd.extend(args)
            
        # Clean environment to prevent environment variable bleeding where necessary
        worker_env = os.environ.copy()
        if env_override:
            worker_env.update(env_override)
            
        # Enforce boundary: run with low priority and redirected streams
        logger.info(f"Forking worker '{worker_name}' with isolated streams: {cmd}")
        
        creation_flags = 0
        if sys.platform == "win32":
            # Below normal priority class
            creation_flags = subprocess.BELOW_NORMAL_PRIORITY_CLASS | getattr(subprocess, "CREATE_NO_WINDOW", 0)
            
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            cwd=self.workspace_dir,
            env=worker_env,
            creationflags=creation_flags,
            text=True
        )
        self.active_workers[worker_name] = proc
        return proc

    def terminate_worker(self, worker_name: str) -> Optional[int]:
        """Safely shuts down the designated worker subprocess, reclaiming host system resources."""
        if worker_name not in self.active_workers:
            return None
            
        proc = self.active_workers[worker_name]
        if proc.poll() is None:
            logger.info(f"Terminating worker process: {worker_name}")
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.warning(f"Worker {worker_name} failed to terminate. Killing process.")
                proc.kill()
                proc.wait()
        
        del self.active_workers[worker_name]
        return proc.returncode

    def get_worker_status(self, worker_name: str) -> str:
        """Get the current process status of a worker."""
        if worker_name not in self.active_workers:
            return "stopped"
        status = self.active_workers[worker_name].poll()
        return "running" if status is None else f"exited_with_{status}"
