import asyncio
import os
import shutil
import tempfile
import time
import uuid
from typing import Any, Dict, Optional

from sandbox.base import ExecutionResult
from tools.registry import ToolDefinition
from security.policy import RiskLevel
from system.state import unified_state

try:
    from sandbox.docker_env import DockerEnvironment
except Exception:
    DockerEnvironment = None


class _StateHook:
    def get_state(self):
        from system.state import unified_state as _state
        return _state.get_state()

    def update(self, key, val):
        from system.state import unified_state as _state
        _state.update(key, val)


class LocalEnvironment:
    """Host-local execution environment used when Docker is unavailable."""

    def __init__(self, timeout_sec: int = 60, max_output_chars: int = 50000, state_hook=None):
        self.timeout_sec = int(timeout_sec)
        self.max_output_chars = int(max_output_chars)
        self.state_hook = state_hook or _StateHook()

        self.workspace_dir = os.getenv("SPARK_WORKSPACE_DIR", os.getcwd())
        self.host_workspace_dir = None

        self.is_running = False
        self.last_cmd = "System ready."
        self.cmd_active = False
        self.active_process = None
        self._snapshots: Dict[str, str] = {}

    def _sync(self):
        self.state_hook.update(
            "sandbox_state",
            {
                "is_running": self.is_running,
                "last_cmd": self.last_cmd,
                "cmd_active": self.cmd_active,
                "mode": "local",
            },
        )

    def cancel_active(self):
        if self.active_process:
            try:
                self.active_process.kill()
            except Exception:
                pass
        self.active_process = None
        self.cmd_active = False
        self.last_cmd = "[CANCELLED]"
        self._sync()

    async def setup(self) -> bool:
        if self.host_workspace_dir:
            self.workspace_dir = self.host_workspace_dir
        self.is_running = True
        self._sync()
        return True

    def _resolve_path(self, path: str) -> str:
        raw = (path or "").strip()
        if not raw:
            base = self.host_workspace_dir or self.workspace_dir
            return os.path.abspath(base)

        base = self.host_workspace_dir or self.workspace_dir
        normalized = raw.replace("\\", "/")

        if normalized.startswith("/workspace"):
            suffix = normalized[len("/workspace"):].lstrip("/")
            return os.path.abspath(os.path.join(base, suffix))

        if os.path.isabs(raw):
            return os.path.abspath(raw)

        return os.path.abspath(os.path.join(base, raw))

    async def run_command(self, cmd: str) -> ExecutionResult:
        self.last_cmd = cmd
        self.cmd_active = True
        self._sync()

        start = time.time()
        cwd = self.host_workspace_dir or self.workspace_dir
        truncated = False
        exit_code = -1
        out_str = ""
        err_str = ""

        process = await asyncio.create_subprocess_shell(
            cmd,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self.active_process = process

        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(),
                timeout=self.timeout_sec,
            )
            out_str = stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else ""
            err_str = stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else ""
            exit_code = process.returncode
        except asyncio.TimeoutError:
            process.kill()
            stdout_bytes, stderr_bytes = await process.communicate()
            out_str = (stdout_bytes.decode("utf-8", errors="replace") if stdout_bytes else "")
            err_str = (stderr_bytes.decode("utf-8", errors="replace") if stderr_bytes else "")
            out_str += f"\n\n[Process killed after {self.timeout_sec}s timeout]"
            exit_code = -1
            truncated = True
        finally:
            self.active_process = None
            self.cmd_active = False
            self._sync()

        if len(out_str) > self.max_output_chars:
            out_str = out_str[: self.max_output_chars] + f"\n\n[Warning: Output truncated to {self.max_output_chars} chars]"
            truncated = True
        if len(err_str) > self.max_output_chars:
            err_str = err_str[: self.max_output_chars] + f"\n\n[Warning: Stderr truncated to {self.max_output_chars} chars]"
            truncated = True

        duration_ms = int((time.time() - start) * 1000)
        return ExecutionResult(
            exit_code=exit_code,
            stdout=out_str.strip(),
            stderr=err_str.strip(),
            duration_ms=duration_ms,
            truncated=truncated,
        )

    async def read_file(self, path: str) -> str:
        resolved = self._resolve_path(path)

        def _read() -> str:
            with open(resolved, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        try:
            return await asyncio.to_thread(_read)
        except Exception:
            return ""

    async def write_file(self, path: str, content: str) -> bool:
        resolved = self._resolve_path(path)

        def _write() -> bool:
            os.makedirs(os.path.dirname(resolved), exist_ok=True)
            with open(resolved, "w", encoding="utf-8", newline="\n") as f:
                f.write(content)
            return True

        try:
            return await asyncio.to_thread(_write)
        except Exception:
            return False

    async def delete_file(self, path: str) -> bool:
        resolved = self._resolve_path(path)

        def _delete() -> bool:
            if os.path.isdir(resolved):
                shutil.rmtree(resolved)
            else:
                os.remove(resolved)
            return True

        try:
            return await asyncio.to_thread(_delete)
        except Exception:
            return False

    async def list_dir(self, path: str = "") -> str:
        resolved = self._resolve_path(path)

        def _list() -> str:
            entries = []
            for name in sorted(os.listdir(resolved)):
                full = os.path.join(resolved, name)
                entries.append(f"{name}/" if os.path.isdir(full) else name)
            return "\n".join(entries)

        try:
            return await asyncio.to_thread(_list)
        except Exception as exc:
            return f"[Error listing dir: {exc}]"

    async def snapshot(self, name: str) -> bool:
        source_root = self.host_workspace_dir or self.workspace_dir
        if not source_root or not os.path.exists(source_root):
            return False

        def _snapshot() -> Optional[str]:
            snapshot_root = tempfile.mkdtemp(prefix=f"spark_snapshot_{name}_")
            target = os.path.join(snapshot_root, "workspace")
            ignore = shutil.ignore_patterns(
                ".git",
                "node_modules",
                "__pycache__",
                "*.pyc",
                "spark_memory_db",
                "spark_dev_memory",
                ".venv",
                "venv",
                "dist",
                "build",
            )
            shutil.copytree(source_root, target, dirs_exist_ok=True, ignore=ignore)
            return target

        try:
            target = await asyncio.to_thread(_snapshot)
            if not target:
                return False
            self._snapshots[name] = target
            return True
        except Exception:
            return False

    async def rollback(self, name: str) -> bool:
        snapshot_target = self._snapshots.get(name)
        source_root = self.host_workspace_dir or self.workspace_dir
        if not snapshot_target or not os.path.exists(snapshot_target) or not source_root:
            return False

        def _rollback() -> bool:
            shutil.copytree(snapshot_target, source_root, dirs_exist_ok=True)
            return True

        try:
            return await asyncio.to_thread(_rollback)
        except Exception:
            return False

    async def teardown(self) -> bool:
        self.cancel_active()
        self.is_running = False
        self._sync()
        return True


class AdaptiveSandbox:
    """Stable sandbox object that can switch backend without breaking imports."""

    def __init__(self):
        self.state_hook = _StateHook()
        self._host_workspace_dir: Optional[str] = None
        self._backend = LocalEnvironment(state_hook=self.state_hook)
        self.mode = "local"

    @property
    def host_workspace_dir(self) -> Optional[str]:
        return self._host_workspace_dir

    @host_workspace_dir.setter
    def host_workspace_dir(self, value: Optional[str]):
        self._host_workspace_dir = value
        if hasattr(self._backend, "host_workspace_dir"):
            self._backend.host_workspace_dir = value

    @property
    def workspace_dir(self) -> str:
        return getattr(self._backend, "workspace_dir", "/workspace")

    @property
    def is_running(self) -> bool:
        return bool(getattr(self._backend, "is_running", False))

    @property
    def last_cmd(self) -> str:
        return str(getattr(self._backend, "last_cmd", "System ready."))

    @property
    def cmd_active(self) -> bool:
        return bool(getattr(self._backend, "cmd_active", False))

    @property
    def active_process(self):
        return getattr(self._backend, "active_process", None)

    async def configure(self, mode: Optional[str] = None) -> bool:
        selected = (mode or os.getenv("SPARK_SANDBOX_MODE", "auto")).strip().lower()
        if selected not in {"auto", "docker", "local"}:
            selected = "auto"

        timeout = int(os.getenv("SPARK_SANDBOX_TIMEOUT_SEC", "60"))

        if selected in {"auto", "docker"} and DockerEnvironment is not None:
            docker_backend = DockerEnvironment(timeout_sec=timeout, state_hook=self.state_hook)
            docker_backend.host_workspace_dir = self.host_workspace_dir
            docker_ok = await docker_backend.setup()
            if docker_ok:
                self._backend = docker_backend
                self.mode = "docker"
                return True
            print("[Sandbox] Docker backend unavailable. Falling back to local mode.")

        local_backend = LocalEnvironment(timeout_sec=timeout, state_hook=self.state_hook)
        local_backend.host_workspace_dir = self.host_workspace_dir
        local_ok = await local_backend.setup()
        if local_ok:
            self._backend = local_backend
            self.mode = "local"
            return True

        return False

    def cancel_active(self):
        cancel = getattr(self._backend, "cancel_active", None)
        if callable(cancel):
            cancel()

    async def setup(self) -> bool:
        return await self._backend.setup()

    async def run_command(self, cmd: str) -> ExecutionResult:
        return await self._backend.run_command(cmd)

    async def read_file(self, path: str) -> str:
        return await self._backend.read_file(path)

    async def write_file(self, path: str, content: str) -> bool:
        return await self._backend.write_file(path, content)

    async def delete_file(self, path: str) -> bool:
        return await self._backend.delete_file(path)

    async def list_dir(self, path: str = "") -> str:
        return await self._backend.list_dir(path)

    async def snapshot(self, name: str) -> bool:
        return await self._backend.snapshot(name)

    async def rollback(self, name: str) -> bool:
        return await self._backend.rollback(name)

    async def teardown(self) -> bool:
        return await self._backend.teardown()


sandbox = AdaptiveSandbox()


def emit_telemetry(action: str, result: str, duration_ms: int = 0):
    task_id = uuid.uuid4().hex[:8]
    state = unified_state.get_state()
    tasks = state.get("active_tasks", [])
    tasks.append(
        {
            "id": task_id,
            "action": action,
            "result": result[:100] + "..." if len(result) > 100 else result,
            "duration_ms": duration_ms,
        }
    )
    unified_state.update("active_tasks", tasks[-10:])


async def init_sandbox():
    ok = await sandbox.configure()
    if ok:
        print(f"[Sandbox] Active backend: {sandbox.mode}")
    else:
        print("[Sandbox] Failed to initialize any backend.")


async def teardown_sandbox():
    await sandbox.teardown()


async def sandbox_shell_exec(args: Dict[str, Any]) -> str:
    """Executes a command in the active sandbox backend."""
    cmd = args.get("command")
    if not cmd:
        return "[ERROR] Missing 'command' argument."

    result = await sandbox.run_command(cmd)
    output = f"Exit Code: {result.exit_code}\n"
    if result.stdout:
        output += f"STDOUT:\n{result.stdout}\n"
    if result.stderr:
        output += f"STDERR:\n{result.stderr}\n"
    emit_telemetry(f"shell: {cmd[:20]}", output, result.duration_ms)
    return output.strip()


async def sandbox_read_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    if not path:
        return "[ERROR] Missing 'path' argument."
    content = await sandbox.read_file(path)
    if content == "":
        return f"[ERROR] Read failed: could not read '{path}'"
    emit_telemetry(f"read: {path}", "Read successful.")
    return content


async def sandbox_write_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    content = args.get("content")
    if not path or content is None:
        return "[ERROR] Missing 'path' or 'content' argument."
    ok = await sandbox.write_file(path, str(content))
    if not ok:
        return f"[ERROR] Write failed for '{path}'"
    res = f"Operation write_file successful to {path}."
    emit_telemetry(f"write: {path}", res)
    return res


async def sandbox_list_dir(args: Dict[str, Any]) -> str:
    path = args.get("path", ".")
    content = await sandbox.list_dir(path)
    emit_telemetry(f"ls: {path}", "Listed OK")
    return content


async def sandbox_delete_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    if not path:
        return "[ERROR] Missing 'path' argument."
    ok = await sandbox.delete_file(path)
    if not ok:
        return f"[ERROR] Delete failed: {path}"
    res = f"Deleted {path}"
    emit_telemetry(f"delete: {path}", res)
    return res


sandbox_tools = [
    ToolDefinition(name="sandbox_shell", handler=sandbox_shell_exec, risk_level=RiskLevel.YELLOW, required_capabilities=["base_user"]),
    ToolDefinition(name="sandbox_read_file", handler=sandbox_read_file, risk_level=RiskLevel.GREEN, required_capabilities=["base_user"]),
    ToolDefinition(name="sandbox_list_dir", handler=sandbox_list_dir, risk_level=RiskLevel.GREEN, required_capabilities=["base_user"]),
    ToolDefinition(name="sandbox_write_file", handler=sandbox_write_file, risk_level=RiskLevel.RED, required_capabilities=["base_user"]),
    ToolDefinition(name="sandbox_delete_file", handler=sandbox_delete_file, risk_level=RiskLevel.RED, required_capabilities=["base_user"]),
]
