import asyncio
import os
import tempfile
import uuid
from sandbox.base import ExecutionEnvironment, ExecutionResult

import time
from system.state import unified_state

class DockerEnvironment(ExecutionEnvironment):
    def __init__(self, container_name: str = "spark_sandbox", image: str = "spark_dev_env", timeout_sec: int = 60, max_output_chars: int = 50000, state_hook=None):
        self.container_name = container_name
        self.image = image
        self.is_running = False
        self.timeout_sec = timeout_sec
        self.max_output_chars = max_output_chars
        self.workspace_dir = "/workspace"
        self.last_cmd = "System ready."
        self.cmd_active = False
        self.active_process = None
        self.state_hook = state_hook

    def _sync(self):
        state_target = self.state_hook if self.state_hook else unified_state
        state_target.update("sandbox_state", {
            "is_running": self.is_running,
            "last_cmd": self.last_cmd,
            "cmd_active": self.cmd_active
        })

    def cancel_active(self):
        if self.active_process:
            try:
                self.active_process.kill()
            except Exception:
                pass
            self.cmd_active = False
            self.last_cmd = "[CANCELLED]"
            self._sync()

    async def _run_subprocess(self, *args, timeout_override: int = None) -> ExecutionResult:
        start_time = time.time()
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        self.active_process = process
        
        timeout = timeout_override or self.timeout_sec
        truncated = False
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(), timeout=timeout)
            out_str = stdout_bytes.decode('utf-8', errors='replace').strip() if stdout_bytes else ""
            err_str = stderr_bytes.decode('utf-8', errors='replace').strip() if stderr_bytes else ""
            exit_code = process.returncode
        except asyncio.TimeoutError:
            process.kill()
            stdout_bytes, stderr_bytes = await process.communicate()
            out_str = stdout_bytes.decode('utf-8', errors='replace').strip() if stdout_bytes else ""
            err_str = stderr_bytes.decode('utf-8', errors='replace').strip() if stderr_bytes else ""
            out_str += f"\n\n[Process killed after {timeout}s timeout]"
            exit_code = -1
            truncated = True
            
        duration_ms = int((time.time() - start_time) * 1000)
        
        if len(out_str) > self.max_output_chars:
            out_str = out_str[:self.max_output_chars] + f"\n\n[Warning: Output truncated to {self.max_output_chars} chars]"
            truncated = True
        if len(err_str) > self.max_output_chars:
            err_str = err_str[:self.max_output_chars] + f"\n\n[Warning: Stderr truncated to {self.max_output_chars} chars]"
            truncated = True
            
        self.active_process = None
        
        return ExecutionResult(
            exit_code=exit_code,
            stdout=out_str,
            stderr=err_str,
            duration_ms=duration_ms,
            truncated=truncated
        )

    async def setup(self) -> bool:
        # Check if running, if yes, we can just use it
        res = await self._run_subprocess("docker", "ps", "-q", "-f", f"name={self.container_name}")
        if res.stdout:
            self.is_running = True
            self._sync()
            return True
        
        # Start a persistent container that sleeps forever so we can exec into it
        print(f"🐳 [DOCKER] Starting sandbox container '{self.container_name}'...")
        res = await self._run_subprocess(
            "docker", "run", "-d", "--name", self.container_name, "-w", self.workspace_dir, self.image, "sleep", "infinity"
        )
        
        if res.success:
            self.is_running = True
            print(f"✅ [DOCKER] Sandbox started: {res.stdout[:12]}")
            self._sync()
            return True
        else:
            print(f"⚠️ [DOCKER] Failed to start sandbox: {res.stderr}")
            self._sync()
            return False

    async def run_command(self, cmd: str) -> ExecutionResult:
        if not self.is_running:
            return ExecutionResult(-1, "", "Sandbox is not running.")
            
        print(f"🐳 [DOCKER] Executing: {cmd}")
        self.last_cmd = cmd
        self.cmd_active = True
        self._sync()
        
        # Execute cmd via bash to support pipelines and builtins
        res = await self._run_subprocess(
            "docker", "exec", self.container_name, "bash", "-c", cmd
        )
        self.cmd_active = False
        self._sync()
        return res

    def _resolve_path(self, path: str) -> str:
        # Prevent escaping the workspace via simple checks (though we're in a container anyway)
        # But this maps relative paths nicely into /workspace/
        if not path.startswith("/"):
            path = os.path.join(self.workspace_dir, path)
        return path

    async def read_file(self, path: str) -> str:
        if not self.is_running:
            return ""
        resolved = self._resolve_path(path)
        res = await self.run_command(f"cat '{resolved}'")
        return res.stdout if res.success else ""

    async def write_file(self, path: str, content: str) -> bool:
        if not self.is_running:
            return False
            
        resolved = self._resolve_path(path)
        # Handle creating director tree internally before copy just in case
        parent_dir = os.path.dirname(resolved)
        await self.run_command(f"mkdir -p '{parent_dir}'")
            
        # Create a temporary local file then `docker cp` it into the container
        tmp_name = os.path.join(tempfile.gettempdir(), f"spark_tmp_{uuid.uuid4().hex}")
        with open(tmp_name, 'w', encoding='utf-8', newline='\n') as f:
            f.write(content)
            
        res = await self._run_subprocess(
            "docker", "cp", tmp_name, f"{self.container_name}:{resolved}"
        )
        
        if os.path.exists(tmp_name):
            try:
                os.remove(tmp_name)
            except Exception:
                pass
                
        if res.success:
            print(f"🐳 [DOCKER] File written to {resolved}")
            return True
        else:
            print(f"⚠️ [DOCKER] Failed to write file: {res.stderr}")
            return False

    async def delete_file(self, path: str) -> bool:
        if not self.is_running:
            return False
        resolved = self._resolve_path(path)
        res = await self.run_command(f"rm -rf '{resolved}'")
        return res.success
        
    async def list_dir(self, path: str = "") -> str:
        if not self.is_running:
            return ""
        resolved = self._resolve_path(path) if path else self.workspace_dir
        res = await self.run_command(f"ls -la '{resolved}'")
        return res.stdout if res.success else f"[Error listing dir: {res.stderr}]"

    async def snapshot(self, name: str) -> bool:
        snapshot_tag = f"spark_snapshot_{name}"
        print(f"🐳 [DOCKER] Committing snapshot '{snapshot_tag}'...")
        res = await self._run_subprocess(
            "docker", "commit", self.container_name, snapshot_tag
        )
        return res.success

    async def rollback(self, name: str) -> bool:
        snapshot_tag = f"spark_snapshot_{name}"
        print(f"🐳 [DOCKER] Rolling back to snapshot '{snapshot_tag}'...")
        
        # Stop and remove current sandbox
        await self.teardown()
        
        # Update image to snapshot and restart
        self.image = snapshot_tag
        return await self.setup()

    async def teardown(self) -> bool:
        print(f"🐳 [DOCKER] Tearing down sandbox '{self.container_name}'...")
        res_stop = await self._run_subprocess("docker", "stop", self.container_name)
        res_rm = await self._run_subprocess("docker", "rm", "-f", self.container_name)
        self.is_running = False
        self._sync()
        return res_stop.success and res_rm.success
