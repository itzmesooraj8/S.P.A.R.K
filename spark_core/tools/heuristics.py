import json
from typing import Dict, Any
from security.policy import ToolDefinition, RiskLevel
from intelligence.heuristics import mutation_heuristics
from tools.sandbox import emit_telemetry

async def heuristics_analyze_mutation_risk(args: Dict[str, Any]) -> str:
    """Analyzes historical telemetry for a given structural node and returns a probabilistic mutation risk profile. This MUST be called before generating a patch for complex or previously failing nodes."""
    target_node = args.get("node_id")
    if not target_node:
        return "⚠️ [ERROR] Missing 'node_id' argument."
        
    profile = mutation_heuristics.analyze_node_history(target_node)
    
    # Store to active telemetry stream
    emit_telemetry(f"risk: {target_node}", f"Risk Level: {profile.get('risk_level')}")
    
    # Return explicit structured JSON for the LLM to directly ingest into its contextual decision loop
    return json.dumps(profile, indent=2)

heuristic_tools = [
     ToolDefinition(
        name="heuristics_analyze_mutation_risk",
        handler=heuristics_analyze_mutation_risk,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"]
    )
]
