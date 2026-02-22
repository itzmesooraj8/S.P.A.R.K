from typing import Dict, Any
from security.policy import ToolDefinition, RiskLevel
from tools.sandbox import sandbox, emit_telemetry
from intelligence.refactor import RefactorEngine
from intelligence.graph import CodeGraph
from tools.testing import test_orchestrator
from tools.intelligence import shared_code_graph

refactor_engine = RefactorEngine(sandbox=sandbox, graph=shared_code_graph, test_orchestrator=test_orchestrator)

async def refactoring_apply_autonomous_patch(args: Dict[str, Any]) -> str:
    """Executes a closed-loop mutation: Snapshot -> Apply Patch -> Validate Tests -> Commits or Rolls Back based on test success."""
    target_node_id = args.get("node_id")
    file_path = args.get("path")
    patch_content = args.get("patch_content")
    
    if not target_node_id or not file_path or not patch_content:
        return "⚠️ [ERROR] Missing required arguments: 'node_id', 'path', or 'patch_content'."
        
    res = await refactor_engine.apply_autonomous_mutation(target_node_id, file_path, patch_content)
    
    emit_telemetry(f"refactor: {target_node_id}", res)
    return res

refactoring_tools = [
    ToolDefinition(
        name="refactoring_apply_autonomous_patch",
        handler=refactoring_apply_autonomous_patch,
        risk_level=RiskLevel.RED, # This is an autonomous mutation, so user confirmation is needed.
        required_capabilities=["base_user"]
    )
]
