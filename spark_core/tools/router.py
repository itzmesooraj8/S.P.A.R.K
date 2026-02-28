import json
import time
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator

from tools.registry import ToolRegistry
from security.policy import SecurityPolicy, ToolDefinition, RiskLevel, RequiresConfirmationError
from system.state import unified_state
from tools.sandbox import sandbox_tools
from tools.intelligence import intelligence_tools
from tools.testing import testing_tools
from tools.refactor import refactoring_tools
from tools.memory import memory_tools
from tools.heuristics import heuristic_tools
from tools.context import context_tools

# --- Default Native Tools ---

async def get_time(args: Dict[str, Any] = None) -> str:
    """Returns the current server time."""
    from datetime import datetime
    now = datetime.now()
    return f"Current System Time: {now.strftime('%Y-%m-%d %H:%M:%S')}"

async def ping_local(args: Dict[str, Any] = None) -> str:
    """Checks if the local SPARK core is responsive."""
    return "SPARK Local Host is ONLINE and operational. Latency minimal."

async def list_capabilities(args: Dict[str, Any] = None) -> str:
    """Lists current system capabilities."""
    return "I can currently access the system time, check my local health status, and stream responses dynamically."

# --------------------------

class ToolRouter:
    """
    Parses LLM intents to detect tool calls, sanitizes execution,
    and streams outputs progressively back to the Orchestrator loop.
    """
    def __init__(self):
        self.registry = ToolRegistry()
        self.policy = SecurityPolicy()
        
        # Self-register native low-risk kernel tools
        self.registry.register(ToolDefinition(name="get_time", handler=get_time, risk_level=RiskLevel.GREEN))
        self.registry.register(ToolDefinition(name="ping", handler=ping_local, risk_level=RiskLevel.GREEN))
        self.registry.register(ToolDefinition(name="list_capabilities", handler=list_capabilities, risk_level=RiskLevel.GREEN))
        for tool in sandbox_tools:
            self.registry.register(tool)
        for tool in intelligence_tools:
            self.registry.register(tool)
        for tool in testing_tools:
            self.registry.register(tool)
        for tool in refactoring_tools:
            self.registry.register(tool)
        for tool in memory_tools:
            self.registry.register(tool)
        for tool in heuristic_tools:
            self.registry.register(tool)
        for tool in context_tools:
            self.registry.register(tool)
        
    def detect_tool_call(self, raw_message: str) -> Optional[Dict[str, Any]]:
        """
        Attempts to parse a strict JSON block from the LLM or user requesting a tool.
        Expects format: {"tool": "tool_name", "arguments": { ... }}
        """
        start_idx = raw_message.find("{")
        if start_idx != -1:
            try:
                data, idx = json.JSONDecoder().raw_decode(raw_message[start_idx:])
                if isinstance(data, dict) and "tool" in data and isinstance(data["tool"], str):
                    args = data.get("arguments", {})
                    if not isinstance(args, dict):
                        args = {}
                    return {"tool": data["tool"], "arguments": args}
            except json.JSONDecodeError:
                pass
                
        return None

    async def execute_raw(self, tool_call: Dict[str, Any]) -> Any:
        """Executes the tool and returns the raw output for LLM reflection."""
        tool_name = tool_call["tool"]
        arguments = tool_call["arguments"]
        tool_def = self.registry.get(tool_name)
        if not tool_def:
            return f"⚠️ [ERROR] execution failed: Tool '{tool_name}' is not registered."
            
        user_caps = unified_state.get_state().get("security_context", {}).get("capabilities", [])
        auth_res = self.policy.authorize(tool_def, user_caps)
        
        if not auth_res.allowed:
            if auth_res.requires_confirmation:
                raise RequiresConfirmationError(tool_call, auth_res.reason)
            return f"⚠️ [BLOCKED] Access denied: {auth_res.reason}"

        return await self._safe_execute_tool(tool_def, arguments)

    async def _safe_execute_tool(self, tool_def, arguments) -> dict:
        """Phase 4: Tool Isolation and Timeout Wrapper with Retries"""
        import traceback
        import inspect
        
        async def _invoke_tool_handler(handler, arguments):
            arguments = arguments or {}
            # Robust calling convention:
            # 1. Try passing as **kwargs
            # 2. Try passing as single 'args' dict
            # 3. Try passing with no args (if empty)
            
            try:
                if isinstance(arguments, dict) and arguments:
                     # If we have distinct keys, try kwargs first
                    try:
                        result = handler(**arguments)
                    except TypeError:
                         # Fallback to single dict arg
                        result = handler(arguments)
                else:
                    # Empty arguments
                    try:
                        result = handler(arguments) # Pass empty dict
                    except TypeError:
                        result = handler() # Pass nothing
                    
                if inspect.isawaitable(result):
                    result = await result
                return result
            except Exception as e:
                return f"⚠️ [ERROR] Tool execution failed: {str(e)}"
        
        max_attempts = getattr(tool_def, 'retries', 0) + 1
        timeout = getattr(tool_def, 'timeout_sec', 30.0)
        
        for attempt in range(max_attempts):
            try:
                result = await asyncio.wait_for(
                    _invoke_tool_handler(tool_def.handler, arguments), 
                    timeout=timeout
                )
                return {
                    "success": True,
                    "output": str(result),
                    "error": None
                }
            except asyncio.TimeoutError:
                print(f"⚠️ [TOOL INTERNAL] Timeout in {tool_def.name} (Attempt {attempt + 1}/{max_attempts})")
                if attempt == max_attempts - 1:
                    return {
                        "success": False,
                        "output": "",
                        "error": f"Tool execution timed out after {timeout}s."
                    }
            except Exception as e:
                # Internal logging ONLY, never leak stack trace to user string
                print(f"⚠️ [TOOL INTERNAL] Crash in {tool_def.name} (Attempt {attempt + 1}/{max_attempts}): {e}")
                traceback.print_exc()
                if attempt == max_attempts - 1:
                    return {
                        "success": False,
                        "output": "",
                        "error": str(e)
                    }
            
            # Small backoff before retry
            await asyncio.sleep(1.0)

    async def execute(self, tool_call: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Executes the registered tool and yields characters sequentially
        to maintain the UI progressive typing illusion.
        """
        tool_name = tool_call["tool"]
        arguments = tool_call["arguments"]
        
        tool_def = self.registry.get(tool_name)
        if not tool_def:
            error_msg = f"⚠️ [ERROR] execution failed: Tool '{tool_name}' is not registered."
            for char in error_msg:
                yield char
                await asyncio.sleep(0.01)
            return

        user_caps = unified_state.get_state().get("security_context", {}).get("capabilities", [])
        auth_res = self.policy.authorize(tool_def, user_caps)
        
        if not auth_res.allowed:
            if auth_res.requires_confirmation:
                raise RequiresConfirmationError(tool_call, auth_res.reason)
            else:
                error_msg = f"⚠️ [BLOCKED] Access denied: {auth_res.reason}"
                for char in error_msg:
                    yield char
                    await asyncio.sleep(0.01)
                return

        print(f"⚙️ [TOOL ROUTER] Executing '{tool_name}' with args: {arguments}")
        # Ensure it is purely non-blocking via safe wrapper
        res_dict = await self._safe_execute_tool(tool_def, arguments)
        
        if res_dict["success"]:
            formatted_result = f"🔧 [KERNEL ACTION: {tool_name.upper()}]\n{res_dict['output']}"
        else:
            formatted_result = f"⚠️ [KERNEL ACTION EXCEPTION: {tool_name.upper()}]\n{res_dict['error']}"
            
        # Stream out to the WebSocket progressively
        for char in formatted_result:
            yield char
            # Add natural typing cadence for tool execution confirmation
            await asyncio.sleep(0.01)
