from typing import Dict, Any
import json
from security.policy import ToolDefinition, RiskLevel
from system.state import unified_state
from tools.sandbox import sandbox, emit_telemetry
from intelligence.graph import CodeGraph
from intelligence.scanner import WorkspaceScanner

shared_code_graph = CodeGraph()

async def intelligence_scan_workspace(args: Dict[str, Any]) -> str:
    """Scans the entire workspace into an AST driven code graph."""
    scanner = WorkspaceScanner(sandbox, shared_code_graph)
    result = await scanner.scan_workspace()
    
    if "error" in result:
        return f"⚠️ [ERROR] Scan failed: {result['error']}"
        
    unified_state.update("code_graph", result)
    
    summary = f"Workspace Scan Complete.\nNodes Extracted: {len(result['nodes'])}\nEdges Discovered: {len(result['edges'])}"
    emit_telemetry("scan:workspace", summary)
    return summary

async def intelligence_query_graph(args: Dict[str, Any]) -> str:
    """Queries the graph for a specific node and its dependencies/callers."""
    node_id = args.get("node_id")
    if not node_id:
        return "⚠️ [ERROR] Missing 'node_id' argument."
        
    node = shared_code_graph.get_node(node_id)
    if not node:
        return f"Node '{node_id}' not found in the code graph. Did you run a workspace scan?"
        
    deps = shared_code_graph.get_dependencies(node_id)
    callers = shared_code_graph.get_callers(node_id)
    
    out = (
        f"Node: {node.id}\n"
        f"Type: {node.type}\n"
        f"File: {node.path} (lines {node.start_line}-{node.end_line})\n"
        f"Signature: {node.signature}\n"
        f"--- Dependencies (imports/calls) ---\n"
        + ("\n".join(deps) if deps else "None") + "\n"
        f"--- Callers (who imports/calls this) ---\n"
        + ("\n".join(callers) if callers else "None")
    )
    
    emit_telemetry(f"graph:query {node_id}", "Queried Node")
    return out

intelligence_tools = [
    ToolDefinition(
        name="intelligence_scan_workspace",
        handler=intelligence_scan_workspace,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="intelligence_query_graph",
        handler=intelligence_query_graph,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"]
    )
]
