from typing import Dict, Any
from security.policy import ToolDefinition, RiskLevel
from memory.dev_memory import dev_memory
from tools.sandbox import emit_telemetry

async def memory_recall_node_mutations(args: Dict[str, Any]) -> str:
    """Queries persistent Dev Memory for past autonomous iterations specifically targeting a codebase node."""
    target_node = args.get("node_id")
    if not target_node:
        return "⚠️ [ERROR] Missing 'node_id' attribute."
        
    results = dev_memory.recall_mutations_for_node(target_node)
    
    if not results:
        return f"🧠 [DEV MEMORY] No prior refactor iterations found in vector DB for node: {target_node}"
        
    out = f"🧠 [DEV MEMORY] Retrieved {len(results)} past mutations for {target_node}:\n\n"
    for r in results:
        dist = r.get("distance", 0.0)
        doc = r.get("document", "Unknown Memory")
        meta = r.get("metadata", {})
        
        status = "✅ PASS" if meta.get("success", False) else "❌ FAIL"
        dur = meta.get("duration_ms", 0)
        out += f"--- [Similarity: {dist:.4f}] ---\nOutcome: {status} ({dur}ms)\nSummary: {doc}\n\n"
        
    emit_telemetry(f"mem:recall {target_node}", f"Recalled {len(results)} items")
    return out

async def memory_search_similar_errors(args: Dict[str, Any]) -> str:
    """Queries persistent Dev Memory to cross-reference a stack trace against historical failures."""
    error_trace = args.get("error_trace")
    if not error_trace:
        return "⚠️ [ERROR] Missing 'error_trace' attribute."
        
    results = dev_memory.search_similar_errors(error_trace)
    
    if not results:
        return "🧠 [DEV MEMORY] No structurally similar mutation failures found in history."
        
    out = f"🧠 [DEV MEMORY] Found {len(results)} related past failures:\n\n"
    for r in results:
        dist = r.get("distance", 0.0)
        doc = r.get("document", "Unknown Memory")
        meta = r.get("metadata", {})
        
        node = meta.get("target_node", "Unknown")
        patch_hash = meta.get("patch_hash", "Unknown")
        out += f"--- [Similarity: {dist:.4f}] ---\nFailed Node: {node}\nPatch Hash: {patch_hash}\nSummary: {doc}\n\n"
        
    emit_telemetry(f"mem:search_err", f"Found {len(results)} matches")
    return out

memory_tools = [
    ToolDefinition(
        name="memory_recall_node_mutations",
        handler=memory_recall_node_mutations,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="memory_search_similar_errors",
        handler=memory_search_similar_errors,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"]
    )
]
