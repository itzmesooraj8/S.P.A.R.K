from typing import Dict, Any
from security.policy import ToolDefinition, RiskLevel
from tools.testing import test_orchestrator
from intelligence.context import context_compiler
from tools.sandbox import emit_telemetry

async def context_build_map(args: Dict[str, Any]) -> str:
    """Forces SPARK to synthetically rebuild its architecture test-to-node line coverage mapping by executing pytest-cov. Costs roughly whatever a full test suite takes to run."""
    success = await test_orchestrator.build_context_map()
    if not success:
        return "⚠️ [ERROR] Failed to compile structural testing context map."
    
    emit_telemetry("context_compile", "Mapped test infrastructure")
    return "✅ [CONTEXT COMPILER] Architectural context map generated explicitly."

async def context_get_node_tests(args: Dict[str, Any]) -> str:
    """Returns the precise test functions that physically execute over a targeted structural CodeNode based on context mapping."""
    target_node = args.get("node_id")
    if not target_node:
        return "⚠️ [ERROR] Missing 'node_id'."
        
    tests = context_compiler.get_tests_for_node(target_node)
    return f"🧠 [CONTEXT] Node {target_node} is directly mapped to tests: {tests}"

async def context_get_downstream_impact(args: Dict[str, Any]) -> str:
    """Returns all structural nodes potentially broken if a specific test node fails natively. Useful for tracking architectural entanglement cascades."""
    test_id = args.get("test_id")
    if not test_id:
        return "⚠️ [ERROR] Missing 'test_id'."
        
    nodes = context_compiler.map_downstream_impact(test_id)
    return f"🔥 [CONTEXT] Failing test {test_id} implicates {len(nodes)} overlapping nodes: {nodes}"


context_tools = [
     ToolDefinition(
        name="context_build_map",
        handler=context_build_map,
        risk_level=RiskLevel.YELLOW,
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="context_get_node_tests",
        handler=context_get_node_tests,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="context_get_downstream_impact",
        handler=context_get_downstream_impact,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"]
    )
]
