from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Callable, Awaitable, Any, List

class RiskLevel(Enum):
    GREEN = auto()    # Safe, read-only
    YELLOW = auto()   # Moderate, requires confirmation
    RED = auto()      # Dangerous, requires strict confirmation
    BLOCKED = auto()  # Disabled completely

@dataclass
class ToolDefinition:
    name: str
    handler: Callable[..., Awaitable[Any]]
    risk_level: RiskLevel = RiskLevel.GREEN
    required_capabilities: List[str] = field(default_factory=list)

class AuthorizationResult:
    def __init__(self, allowed: bool, requires_confirmation: bool = False, reason: str = ""):
        self.allowed = allowed
        self.requires_confirmation = requires_confirmation
        self.reason = reason
        
    def __str__(self):
        return f"AuthorizationResult(allowed={self.allowed}, requires_confirmation={self.requires_confirmation}, reason='{self.reason}')"

class RequiresConfirmationError(Exception):
    def __init__(self, tool_call: dict, reason: str):
        self.tool_call = tool_call
        self.reason = reason
        super().__init__(self.reason)

class SecurityPolicy:
    def __init__(self):
        pass

    def authorize(self, tool_def: ToolDefinition, user_capabilities: List[str]) -> AuthorizationResult:
        if tool_def.risk_level == RiskLevel.BLOCKED:
            return AuthorizationResult(False, False, f"Tool '{tool_def.name}' is BLOCKED by system policy.")
            
        for req_cap in tool_def.required_capabilities:
            if req_cap not in user_capabilities:
                return AuthorizationResult(False, False, f"Missing required capability: {req_cap}")
                
        if tool_def.risk_level in (RiskLevel.YELLOW, RiskLevel.RED):
            return AuthorizationResult(False, True, f"Tool '{tool_def.name}' requires execution confirmation (Risk: {tool_def.risk_level.name}).")
            
        return AuthorizationResult(True, False, "Authorized.")
