from typing import Callable, Dict, Any, Awaitable, List
from security.policy import ToolDefinition, RiskLevel

class ToolRegistry:
    """
    Central registry for SPARK OS tool execution.
    Only authorized async handlers should be bound here.
    """
    def __init__(self):
        self.tools: Dict[str, ToolDefinition] = {}

    def register(self, definition: ToolDefinition):
        self.tools[definition.name] = definition
        print(f"🔧 [TOOL REGISTRY] Registered: {definition.name} (Risk: {definition.risk_level.name})")

    def get(self, name: str) -> ToolDefinition:
        return self.tools.get(name)

    def list_tools(self) -> list:
        return list(self.tools.keys())
