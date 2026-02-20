from typing import Callable, Dict, Any, Awaitable

class ToolRegistry:
    """
    Central registry for SPARK OS tool execution.
    Only authorized async handlers should be bound here.
    """
    def __init__(self):
        self.tools: Dict[str, Callable[..., Awaitable[Any]]] = {}

    def register(self, name: str, handler: Callable[..., Awaitable[Any]]):
        self.tools[name] = handler
        print(f"🔧 [TOOL REGISTRY] Registered: {name}")

    def get(self, name: str) -> Callable[..., Awaitable[Any]]:
        return self.tools.get(name)

    def list_tools(self) -> list:
        return list(self.tools.keys())
