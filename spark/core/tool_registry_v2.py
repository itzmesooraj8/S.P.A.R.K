
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass

class RiskLevel(Enum):
    GREEN = 1   # Read-only / Safe / Analysis
    YELLOW = 2  # State Modified / Low Impact (Create file)
    RED = 3     # Critical / High Impact (Delete, Auth)
    BLOCKED = 4 # Never Allowed (System critical)

@dataclass
class ToolDefinition:
    name: str
    description: str
    risk_level: RiskLevel
    args_schema: Dict[str, str] # Simple schema for now: arg_name -> type
    confirmation_required: bool = False
    auth_required: bool = False
    blocked_patterns: Optional[list] = None # Regex list for arguments to block

class ToolRegistryV2:
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}
        self._register_core_tools()

    def _register_core_tools(self):
        # 1. System Awareness (Green)
        self.register("system_status", "Check CPU/RAM/Battery", RiskLevel.GREEN, {})
        self.register("get_active_window", "Check current app", RiskLevel.GREEN, {})
        
        # 2. Information (Green)
        self.register("search_web", "Search DuckDuckGo", RiskLevel.GREEN, {"query": "str"})
        self.register("read_file", "Read file content", RiskLevel.GREEN, {"path": "str"})
        
        # 3. Low Impact Actions (Yellow)
        self.register("write_file", "Create/Edit file", RiskLevel.YELLOW, 
                     {"path": "str", "content": "str"}, confirmation_required=True)
        self.register("open_app", "Launch application", RiskLevel.YELLOW, 
                     {"app_name": "str"})

        # 4. Critical Actions (Red)
        self.register("delete_file", "Delete a file", RiskLevel.RED, 
                     {"path": "str"}, confirmation_required=True, auth_required=True)
        self.register("system_shutdown", "Shutdown PC", RiskLevel.RED, 
                     {}, confirmation_required=True, auth_required=True)
        
        # 5. Dangerous / Blocked Contexts (Handled by logic, not tool existence usually)
        # But we can register a "terminal" tool with blocked patterns
        self.register("terminal_command", "Run shell command", RiskLevel.RED,
                     {"command": "str"}, confirmation_required=True, 
                     blocked_patterns=[r"rm -rf", r"format", r"del system32"])

    def register(self, name, desc, risk, schema, **kwargs):
        self.tools[name] = ToolDefinition(name, desc, risk, schema, **kwargs)

    def get_tool(self, name) -> Optional[ToolDefinition]:
        return self.tools.get(name)

# Global v2 registry
tool_registry_v2 = ToolRegistryV2()
