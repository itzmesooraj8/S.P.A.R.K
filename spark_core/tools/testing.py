from typing import Dict, Any, List
import json
from security.policy import ToolDefinition, RiskLevel
from system.state import unified_state
from tools.sandbox import sandbox, emit_telemetry
from testing.orchestrator import TestOrchestrator

test_orchestrator = TestOrchestrator(sandbox)

async def testing_discover_tests(args: Dict[str, Any]) -> str:
    """Discovers all tests in the workspace and updates the UnifiedState."""
    path = args.get("path", ".")
    
    tests = await test_orchestrator.discover_tests(path)
    unified_state.update("test_registry", tests)
    
    summary = f"🧪 [TEST DISCOVERY] Found {len(tests)} tests in {path}."
    emit_telemetry("test:discover", summary)
    return summary

async def testing_run_tests(args: Dict[str, Any]) -> str:
    """Runs tests and updates the test_history in UnifiedState."""
    test_nodes = args.get("nodes", [])
    
    results = await test_orchestrator.run_tests(test_nodes)
    
    # Format current run history
    state = unified_state.get_state()
    history = state.get("test_history", [])
    
    run_records = []
    passed = 0
    failed = 0
    for r in results:
        rec = {
            "name": r.name,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "error_trace": r.error_trace
        }
        run_records.append(rec)
        if r.status == "passed": passed += 1
        elif r.status == "failed": failed += 1
        
    history.append({
        "timestamp": state["metrics"]["timestamp"],
        "nodes_requested": test_nodes,
        "results": run_records,
        "passed": passed,
        "failed": failed,
        "total": len(results)
    })
    
    # Keep last 5 test runs
    unified_state.update("test_history", history[-5:])
    
    summary = f"🧪 [TEST RUN] Executed {len(results)} tests. Passed: {passed}, Failed: {failed}."
    emit_telemetry("test:run", summary)
    
    if failed > 0:
        return f"{summary}\n\nSome tests failed. Use 'testing_get_last_failure' or view history for details."
    return summary

async def testing_get_last_failure(args: Dict[str, Any]) -> str:
    """Helper tool to dump the error trace of the last failed test suite."""
    state = unified_state.get_state()
    history = state.get("test_history", [])
    if not history:
        return "No test history."
        
    last_run = history[-1]
    if last_run["failed"] == 0:
        return "Last test run passed successfully! No failures."
        
    out = "💥 [LAST TEST FAILURES]\n"
    for r in last_run["results"]:
        if r["status"] == "failed":
            out += f"\n❌ {r['name']}\nReason:\n{r['error_trace']}\n{'-'*30}"
            
    return out

testing_tools = [
    ToolDefinition(
        name="testing_discover_tests",
        handler=testing_discover_tests,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="testing_run_tests",
        handler=testing_run_tests,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"]
    ),
    ToolDefinition(
        name="testing_get_last_failure",
        handler=testing_get_last_failure,
        risk_level=RiskLevel.GREEN,
        required_capabilities=["base_user"]
    )
]
