import json
import time
import asyncio
from typing import Optional, Dict, Any, AsyncGenerator

from tools.registry import ToolRegistry

# --- Default Native Tools ---

async def get_time(args: Dict[str, Any]) -> str:
    from datetime import datetime
    now = datetime.now()
    return f"Current System Time: {now.strftime('%Y-%m-%d %H:%M:%S')}"

async def ping_local(args: Dict[str, Any]) -> str:
    return "SPARK Local Host is ONLINE and operational. Latency minimal."

async def list_capabilities(args: Dict[str, Any]) -> str:
    return "I can currently access the system time, check my local health status, and stream responses dynamically."

# --------------------------

class ToolRouter:
    """
    Parses LLM intents to detect tool calls, sanitizes execution,
    and streams outputs progressively back to the Orchestrator loop.
    """
    def __init__(self):
        self.registry = ToolRegistry()
        
        # Self-register native low-risk kernel tools
        self.registry.register("get_time", get_time)
        self.registry.register("ping", ping_local)
        self.registry.register("list_capabilities", list_capabilities)
        
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
                
        # Future: If you want to detect "markdown" formatted ```json blocks from Ollama, you extend here.
        return None

    async def execute_raw(self, tool_call: Dict[str, Any]) -> Any:
        """Executes the tool and returns the raw output for LLM reflection."""
        tool_name = tool_call["tool"]
        arguments = tool_call["arguments"]
        handler = self.registry.get(tool_name)
        if not handler:
            return f"⚠️ [ERROR] execution failed: Tool '{tool_name}' is not registered."
        try:
            return await handler(arguments)
        except Exception as e:
            return f"⚠️ [CRITICAL] Tool '{tool_name}' crashed during execution: {e}"

    async def execute(self, tool_call: Dict[str, Any]) -> AsyncGenerator[str, None]:
        """
        Executes the registered tool and yields characters sequentially
        to maintain the UI progressive typing illusion.
        """
        tool_name = tool_call["tool"]
        arguments = tool_call["arguments"]
        
        handler = self.registry.get(tool_name)
        if not handler:
            error_msg = f"⚠️ [ERROR] execution failed: Tool '{tool_name}' is not registered."
            for char in error_msg:
                yield char
                await asyncio.sleep(0.01)
            return

        try:
            print(f"⚙️ [TOOL ROUTER] Executing '{tool_name}' with args: {arguments}")
            # Ensure it is purely non-blocking
            result = await handler(arguments)
            
            # Format result textually 
            formatted_result = f"🔧 [KERNEL ACTION: {tool_name.upper()}]\n{result}"
            
            # Stream out to the WebSocket progressively
            for char in formatted_result:
                yield char
                # Add natural typing cadence for tool execution confirmation
                await asyncio.sleep(0.01)
                
        except Exception as e:
            error_msg = f"⚠️ [CRITICAL] Tool '{tool_name}' crashed during execution: {e}"
            for char in error_msg:
                yield char
                await asyncio.sleep(0.01)
