from spark.modules.iot_bridge import iot_bridge
from spark.modules.services import service_assistant
from core.vault import spark_vault
import json

class ToolRegistry:
    def __init__(self):
        self.sensitive_tools = ["send_email", "set_device_state", "terminal_command"]

    def dispatch(self, tool_name, **kwargs):
        """
        Dispatches a tool call to the appropriate module.
        """
        print(f"[REGISTRY] Dispatching tool: {tool_name} with args: {kwargs}")
        
        # Phase 5: IoT
        if tool_name == "set_device_state":
            return iot_bridge.set_device_state(kwargs.get("topic"), kwargs.get("state"))
        
        # Phase 4/5: Services
        elif tool_name == "get_calendar":
            return service_assistant.get_calendar_events(kwargs.get("count", 3))
        
        elif tool_name == "draft_email":
            return service_assistant.draft_email(
                kwargs.get("recipient"), 
                kwargs.get("subject"), 
                kwargs.get("body")
            )
        
        elif tool_name == "send_email":
            return service_assistant.send_email(kwargs.get("draft_id"))
        
        # Phase 5: Vault (Internal use or management)
        elif tool_name == "store_secret":
            spark_vault.set_secret(kwargs.get("name"), kwargs.get("value"))
            return f"Secret {kwargs.get('name')} stored securely."
            
        else:
            return f"Unknown tool: {tool_name}"

# Global registry
spark_tools = ToolRegistry()

if __name__ == "__main__":
    # Test dispatch
    print(spark_tools.dispatch("get_calendar", count=1))
