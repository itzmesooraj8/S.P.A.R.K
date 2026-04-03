import subprocess
import uuid
import os
from typing import Dict, Any
from tools.registry import ToolDefinition
from security.policy import RiskLevel
from system.state import unified_state

async def init_sandbox():
    print("✅ [Sandbox] Subprocess local execution initialized (Docker removed).")

async def teardown_sandbox():
    pass

class _StateHook:
    def get_state(self):
        from system.state import unified_state
        return unified_state.get_state()
    def update(self, key, val):
        from system.state import unified_state
        unified_state.update(key, val)

class _MockSandbox:
    def __init__(self):
        self.host_workspace_dir = None
        self.workspace_dir = "/workspace"
        self.state_hook = _StateHook()

sandbox = _MockSandbox()

def emit_telemetry(action: str, result: str, duration_ms: int = 0):
    task_id = uuid.uuid4().hex[:8]
    state = unified_state.get_state()
    tasks = state.get("active_tasks", [])
    tasks.append({
        "id": task_id,
        "action": action,
        "result": result[:100] + "..." if len(result) > 100 else result,
        "duration_ms": duration_ms
    })
    unified_state.update("active_tasks", tasks[-10:])

async def sandbox_shell_exec(args: Dict[str, Any]) -> str:
    """Executes a bash/powershell command safely directly on local machine."""
    cmd = args.get("command")
    if not cmd:
        return "⚠️ [ERROR] Missing 'command' argument."
        
    try:
        # Cross-platform execution directly on host
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        output = f"Exit Code: {res.returncode}\n"
        if res.stdout:
            output += f"STDOUT:\n{res.stdout}\n"
        if res.stderr:
            output += f"STDERR:\n{res.stderr}\n"
        emit_telemetry(f"shell: {cmd[:20]}", output, 0)
        return output.strip()
    except subprocess.TimeoutExpired:
        return "⚠️ [ERROR] Command timed out after 60 seconds."
    except Exception as e:
        return f"⚠️ [ERROR] Command execution failed: {str(e)}"

async def sandbox_read_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    if not path: return "⚠️ [ERROR] Missing 'path' argument."
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        emit_telemetry(f"read: {path}", "Read successful.")
        return content
    except Exception as e:
        return f"⚠️ [ERROR] Read failed: {e}"

async def sandbox_write_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    content = args.get("content")
    if not path or not content: return "⚠️ [ERROR] Missing 'path' or 'content' argument."
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        res = f"Operation write_file successful to {path}."
        emit_telemetry(f"write: {path}", res)
        return res
    except Exception as e:
        return f"⚠️ [ERROR] Write failed: {e}"

async def sandbox_list_dir(args: Dict[str, Any]) -> str:
    path = args.get("path", ".")
    try:
        items = os.listdir(path)
        content = "\n".join(items)
        emit_telemetry(f"ls: {path}", "Listed OK")
        return content
    except Exception as e:
        return f"⚠️ [ERROR] ls failed: {e}"

async def sandbox_delete_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    if not path: return "⚠️ [ERROR] Missing 'path' argument."
    try:
        os.remove(path)
        res = f"Deleted {path}"
        emit_telemetry(f"delete: {path}", res)
        return res
    except Exception as e:
        return f"⚠️ [ERROR] Delete failed: {e}"

sandbox_tools = [
    ToolDefinition(name="sandbox_shell", handler=sandbox_shell_exec, risk_level=RiskLevel.YELLOW, required_capabilities=["base_user"]),
    ToolDefinition(name="sandbox_read_file", handler=sandbox_read_file, risk_level=RiskLevel.GREEN, required_capabilities=["base_user"]),
    ToolDefinition(name="sandbox_list_dir", handler=sandbox_list_dir, risk_level=RiskLevel.GREEN, required_capabilities=["base_user"]),
    ToolDefinition(name="sandbox_write_file", handler=sandbox_write_file, risk_level=RiskLevel.RED, required_capabilities=["base_user"]),
    ToolDefinition(name="sandbox_delete_file", handler=sandbox_delete_file, risk_level=RiskLevel.RED, required_capabilities=["base_user"])
]
