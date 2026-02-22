from typing import Dict, Any
from sandbox.docker_env import DockerEnvironment
from tools.registry import ToolDefinition
from security.policy import RiskLevel
from system.state import unified_state
import uuid

# Singleton Sandbox instance
sandbox = DockerEnvironment(container_name="spark_sandbox", image="spark_dev_env")

async def init_sandbox():
    await sandbox.setup()

async def teardown_sandbox():
    await sandbox.teardown()

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
    # Keep only the last 10 tasks
    unified_state.update("active_tasks", tasks[-10:])


async def _safe_red_operation(action_name: str, op_func, *args, **kwargs) -> str:
    """Wrapper that ensures auto-snapshot and rollback on failure for RED operations."""
    snap_id = f"snap_pre_{action_name}_{uuid.uuid4().hex[:6]}"
    await sandbox.snapshot(snap_id)
    
    try:
        success = await op_func(*args, **kwargs)
        if hasattr(success, "success"): # If ExecutionResult
             if not success.success:
                  raise Exception(f"Exit code {success.exit_code}: {success.stderr}")
             return f"Operation {action_name} successful.\nstdout: {success.stdout}"
             
        if not success:
             raise Exception("Operation returned False")
             
        return f"Operation {action_name} successful."
    except Exception as e:
        await sandbox.rollback(snap_id)
        return f"⚠️ [ERROR] Operation {action_name} failed. Automatic rollback performed. Error: {str(e)}"


# -------------------------------------
# TOOL HANDLERS
# -------------------------------------

async def sandbox_shell_exec(args: Dict[str, Any]) -> str:
    """Executes a bash command safely inside the Docker Sandbox."""
    cmd = args.get("command")
    if not cmd:
        return "⚠️ [ERROR] Missing 'command' argument."
        
    res = await sandbox.run_command(cmd)
    
    output = f"Exit Code: {res.exit_code} (Duration: {res.duration_ms}ms)\n"
    if res.stdout:
        output += f"STDOUT:\n{res.stdout}\n"
    if res.stderr:
        output += f"STDERR:\n{res.stderr}\n"
        
    if res.truncated:
        output += "[TRUNCATED]"
        
    emit_telemetry(f"shell: {cmd[:20]}", output, res.duration_ms)
    return output.strip()

async def sandbox_read_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    if not path: return "⚠️ [ERROR] Missing 'path' argument."
    content = await sandbox.read_file(path)
    emit_telemetry(f"read: {path}", "Read successful." if content else "File empty or not found.")
    return content

async def sandbox_write_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    content = args.get("content")
    if not path or not content: return "⚠️ [ERROR] Missing 'path' or 'content' argument."
    
    # Destructive RED operation
    res = await _safe_red_operation("write_file", sandbox.write_file, path, content)
    emit_telemetry(f"write: {path}", res)
    return res

async def sandbox_list_dir(args: Dict[str, Any]) -> str:
    path = args.get("path", "/workspace")
    content = await sandbox.list_dir(path)
    emit_telemetry(f"ls: {path}", "Listed OK")
    return content

async def sandbox_delete_file(args: Dict[str, Any]) -> str:
    path = args.get("path")
    if not path: return "⚠️ [ERROR] Missing 'path' argument."
    
    # Destructive RED operation
    res = await _safe_red_operation("delete_file", sandbox.delete_file, path)
    emit_telemetry(f"delete: {path}", res)
    return res

async def sandbox_apply_patch(args: Dict[str, Any]) -> str:
    # Just an alias over bash `patch`
    path = args.get("path")
    patch_content = args.get("patch_content")
    if not path or not patch_content: return "⚠️ [ERROR] Missing 'path' or 'patch_content'."
    
    patch_path = path + ".patch"
    await sandbox.write_file(patch_path, patch_content)
    
    # Destructive RED operation
    res = await _safe_red_operation("apply_patch", sandbox.run_command, f"patch -u '{path}' -i '{patch_path}' && rm '{patch_path}'")
    emit_telemetry(f"patch: {path}", res)
    return res


# -------------------------------------
# TOOL DEFINITIONS FOR REGISTRY
# -------------------------------------

sandbox_tools = [
    ToolDefinition(
        name="sandbox_shell",
        handler=sandbox_shell_exec,
        risk_level=RiskLevel.YELLOW, 
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="sandbox_read_file",
        handler=sandbox_read_file,
        risk_level=RiskLevel.GREEN, 
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="sandbox_list_dir",
        handler=sandbox_list_dir,
        risk_level=RiskLevel.GREEN, 
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="sandbox_write_file",
        handler=sandbox_write_file,
        risk_level=RiskLevel.RED, 
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="sandbox_delete_file",
        handler=sandbox_delete_file,
        risk_level=RiskLevel.RED, 
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="sandbox_apply_patch",
        handler=sandbox_apply_patch,
        risk_level=RiskLevel.RED, 
        required_capabilities=["base_user"]
    )
]
