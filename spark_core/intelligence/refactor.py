import uuid
import time
from typing import List, Dict, Any, Optional
from sandbox.docker_env import DockerEnvironment
from intelligence.graph import CodeGraph
from testing.orchestrator import TestOrchestrator
from system.state import unified_state
from intelligence.mutation_log import append_mutation_log

class RefactorEngine:
    def __init__(self, sandbox: DockerEnvironment, graph: CodeGraph, test_orchestrator: TestOrchestrator):
        self.sandbox = sandbox
        self.graph = graph
        self.test_orchestrator = test_orchestrator

    async def _run_relevant_tests(self, node_id: str) -> Dict[str, Any]:
        """
        Runs tests mapping to a specific graph node.
        If node is unknown, runs all tests as fallback.
        """
        target_tests = []
        
        # Pull global test signature array
        state = unified_state.get_state()
        known_tests = state.get("test_registry", [])
        
        if not known_tests:
            # Maybe tests haven't been discovered yet.
            known_tests = await self.test_orchestrator.discover_tests()
            
        if self.graph.get_node(node_id):
            # Graph resolves caller trees. Find everything that calls this node.
            callers = self.graph.get_callers(node_id)
            
            # Simple heuristic: If a test module matches the node module, or imports the node, it runs.
            # In a mature implementation, AST nodes of test functions specifically map dependencies.
            # For iteration 1: simple text-mapping against callers space or full test run.
            for test_sig in known_tests:
                if any(ext_c in test_sig for ext_c in callers) or node_id in test_sig:
                    target_tests.append(test_sig)
                    
        # Fallback to run all tests if graph extraction hasn't resolved explicitly.
        if not target_tests:
            print("⚠️ [REFACTOR ENGINE] Exact caller tree unknown. Running ALL validations to be safe.")
            target_tests = ["."]
            
        print(f"⚙️ [REFACTOR ENGINE] Triggering selective test nodes: {target_tests}")
        results = await self.test_orchestrator.run_tests(target_tests)
        
        passed = sum(1 for r in results if r.status == "passed")
        failed = sum(1 for r in results if r.status == "failed")
        
        return {
            "success": failed == 0,
            "passed": passed,
            "failed": failed,
            "results": results
        }

    async def apply_autonomous_mutation(self, target_node_id: str, file_path: str, patch_content: str) -> str:
        """
        Closed Loop:
        1. Snapshot
        2. Patch
        3. Validate
        4. Rollback (if failed) / Commit (if passed)
        """
        snapshot_id = f"refactor_pre_{uuid.uuid4().hex[:6]}"
        print(f"🧬 [REFACTOR ENGINE] Initiating Autonomous Loop for: {target_node_id}")
        
        # 1. Snapshot
        await self.sandbox.snapshot(snapshot_id)
        start_time = time.time()
        
        # 2. Patch
        # Write patch file
        patch_path = f"{file_path}.patch"
        write_res = await self.sandbox.write_file(patch_path, patch_content)
        if not write_res:
            return "⚠️ [ERROR] Failed to stream patch to sandbox. Operation aborted."
            
        # Apply patch via bash natively
        patch_cmd = f"patch -u '{file_path}' -i '{patch_path}' && rm '{patch_path}'"
        res_patch = await self.sandbox.run_command(patch_cmd)
        
        if not res_patch.success:
            await self.sandbox.rollback(snapshot_id)
            return f"❌ [REFACTOR FAIL] Patch application failed. Rolled back.\nError: {res_patch.stderr}"
            
        # 3. Validate
        print("🧬 [REFACTOR ENGINE] Patch absolute. Yielding to Test Orchestrator...")
        validation = await self._run_relevant_tests(target_node_id)
        
        duration = int((time.time() - start_time) * 1000)
        
        # 4. Rollback or Commit
        if not validation["success"]:
            print("❌ [REFACTOR FAIL] Validation failed post-mutation. Rolling back...")
            await self.sandbox.rollback(snapshot_id)
            
            # Fetch the specific error that triggered the failure
            first_fail = next((r.error_trace for r in validation["results"] if r.status == "failed"), "Unknown")
            
            append_mutation_log(
                target_node=target_node_id,
                patch_content=patch_content,
                success=False,
                test_impact=validation,
                duration_ms=duration,
                error_trace=first_fail
            )
            
            return (
                f"❌ [REFACTOR REJECTED] Mutation created test regressions. Safely rolled back.\n"
                f"Node: {target_node_id}\n"
                f"Failed tests: {validation['failed']}\n"
                f"Primary Trigger:\n{first_fail[:500]}\n"
                f"Duration: {duration}ms"
            )
            
        # Success. Keep state. Delete rollback checkpoint to save disk over time.
        await self.sandbox.run_command(f"docker rmi spark_snapshot_{snapshot_id}")
        
        append_mutation_log(
            target_node=target_node_id,
            patch_content=patch_content,
            success=True,
            test_impact=validation,
            duration_ms=duration
        )
        
        return (
            f"✅ [REFACTOR SUCCESS] Mutation validated and applied safely.\n"
            f"Node: {target_node_id}\n"
            f"Tests Passed: {validation['passed']}\n"
            f"Duration: {duration}ms"
        )
