
import re
import structlog
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass

from spark.core.tool_registry_v2 import tool_registry_v2, RiskLevel
from spark.modules.brain_manager import brain_manager

logger = structlog.get_logger()

class EventType(Enum):
    RESPONSE = "response"                # Just speak (no action)
    CONFIRMATION_REQUIRED = "confirm"    # Ask user (Yellow/Red)
    AUTH_REQUIRED = "auth"               # Ask password/bio (Red)
    TOOL_EXECUTION = "execute"           # Run immediately (Green)
    ERROR = "error"                      # System error

@dataclass
class OrchestratorEvent:
    type: EventType
    payload: Any # Text str, or Dict with {tool, args}

class Orchestrator:
    def __init__(self):
        self.pending_action: Optional[Dict] = None # {tool: str, args: dict, risk: level}
        
    async def process_user_input(self, user_text: str) -> OrchestratorEvent:
        """
        Main Decision Pipeline:
        1. Check Persistence (Are we waiting for confirmation?)
        2. Classify Intent (Brain)
        3. Validate & Risk Assess
        4. Return Decision Event
        """
        
        # 1. Check Pending Confirmation
        if self.pending_action:
            if self._is_confirmation(user_text):
                # User said "Yes" -> Execute stored action
                action = self.pending_action
                self.pending_action = None # Clear state
                return OrchestratorEvent(EventType.TOOL_EXECUTION, action)
            elif self._is_denial(user_text):
                # User said "No" -> Cancel
                self.pending_action = None
                return OrchestratorEvent(EventType.RESPONSE, "Action cancelled.")
            else:
                # User said something unrelated -> Clear state? Or keep waiting?
                # "SPARK Safe Rule": If ambiguous, cancel.
                self.pending_action = None
                return OrchestratorEvent(EventType.RESPONSE, "I didn't hear a confirmation, so I cancelled the action.")

        # 2. Classify Intent (Hybrid)
        # Brain thinks -> Returns text which might contain [EXECUTE:...] pattern
        
        full_response = ""
        tool_call = None
        
        # We capture the full thought process
        async for chunk in brain_manager.think(user_text):
            full_response += chunk
            
        # 3. Parse Logic (Regex for now)
        tool_call = self._parse_tool_trigger(full_response)
        
        if tool_call:
            # We found an intent to act.
            # 4. Assess Risk
            tool_name = tool_call['tool']
            args = tool_call['args']
            
            tool_def = tool_registry_v2.get_tool(tool_name)
            if not tool_def:
                # If we don't know the tool in V2 registry, maybe it's legacy?
                # Ideally we map legacy tools to V2 definitions.
                # For now, if not in V2, we default to block/error for safety.
                return OrchestratorEvent(EventType.ERROR, f"Brain tried to use unknown tool: {tool_name}")

            # Check Blocked Patterns
            if tool_def.blocked_patterns:
                for pattern in tool_def.blocked_patterns:
                    # Check args values
                    try:
                         if any(re.search(pattern, str(v)) for v in args.values() if v):
                             return OrchestratorEvent(EventType.ERROR, "Action BLOCKED by safety protocol.")
                    except:
                        pass # Regex error?

            # Decision Matrix
            if tool_def.risk_level == RiskLevel.GREEN:
                # Auto Execute
                return OrchestratorEvent(EventType.TOOL_EXECUTION, tool_call)
            
            elif tool_def.risk_level == RiskLevel.YELLOW:
                # Confirm
                self.pending_action = tool_call
                return OrchestratorEvent(EventType.CONFIRMATION_REQUIRED, f"I need to {tool_def.description}. Proceed?")
                
            elif tool_def.risk_level == RiskLevel.RED:
                # Auth + Confirm
                self.pending_action = tool_call
                return OrchestratorEvent(EventType.AUTH_REQUIRED, "High security action. Authorization required.")
                
            elif tool_def.risk_level == RiskLevel.BLOCKED:
                 return OrchestratorEvent(EventType.ERROR, "This action is globally BLOCKED.")

        # Fallback: Just a conversation response
        return OrchestratorEvent(EventType.RESPONSE, full_response)

    def _is_confirmation(self, text):
        return any(w in text.lower() for w in ["yes", "proceed", "do it", "confirm", "sure", "okay"])

    def _is_denial(self, text):
         return any(w in text.lower() for w in ["no", "stop", "cancel", "don't", "wait", "abort"])

    def _parse_tool_trigger(self, text):
        # Legacy regex from previous tool system, adapted
        match = re.search(r"\[EXECUTE:\s*(\w+)\((.*)\)\]", text)
        if match:
            # Basic arg parsing
            args_str = match.group(2)
            # Try to be smart about args? For now, dict with 'raw' or single arg assumption
            # The registry V2 expects schema. 
            # Legacy only supported single arg usually?
            # We'll return a dict assuming single arg 'query' or 'path' based on tool? 
            # Or just pass raw args string if tool handles it?
            # V2 registry expects dict.
            # We will perform a simplified mapping:
            return {"tool": match.group(1), "args": {"raw": args_str}} 
        return None

# Global Instance
orchestrator = Orchestrator()
