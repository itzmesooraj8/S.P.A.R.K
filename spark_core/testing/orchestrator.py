from dataclasses import dataclass, field
from typing import Literal, List, Dict, Optional
import json
from intelligence.context import context_compiler

@dataclass
class TestResult:
    name: str # The test identifier, e.g., test_module.py::test_func
    status: Literal["passed", "failed", "skipped", "error"]
    duration_ms: int
    error_trace: Optional[str] = None

class TestOrchestrator:
    def __init__(self, sandbox):
        self.sandbox = sandbox
        self.is_setup = False

    async def _ensure_test_env(self) -> bool:
        if self.is_setup:
            return True
            
        print("🧪 [TEST ORCHESTRATOR] Connecting to prebuilt test environment...")
        self.is_setup = True
        return True

    async def discover_tests(self, path: str = ".") -> List[str]:
        """
        Runs pytest --collect-only to find all test signatures.
        """
        ready = await self._ensure_test_env()
        if not ready:
            return []
            
        print(f"🧪 [TEST ORCHESTRATOR] Discovering tests in {path}...")
        # Run pytest --collect-only with json report to parse it reliably
        # Sometimes collect-only doesn't output json-report easily, so we use a dry-run or --quiet trick
        cmd = f"python3 -m pytest {path} --collect-only -q"
        res = await self.sandbox.run_command(cmd)
        
        tests = []
        for line in res.stdout.split('\n'):
            line = line.strip()
            # pytest -q collect-only outputs test node ids like: tests/test_math.py::test_add
            if '::' in line and not line.startswith('warnings'):
                tests.append(line)
                
        print(f"✅ [TEST ORCHESTRATOR] Discovered {len(tests)} tests.")
        return tests

    async def run_tests(self, test_nodes: List[str] = None) -> List[TestResult]:
        """
        Runs specific tests or all tests if none specified.
        Uses pytest-json-report for structured output.
        """
        ready = await self._ensure_test_env()
        if not ready:
            return []
            
        targets = " ".join(test_nodes) if test_nodes else "."
        print(f"🧪 [TEST ORCHESTRATOR] Running tests: {targets or 'ALL'}")
        
        json_report_path = "/workspace/.report.json"
        cmd = f"python3 -m pytest {targets} --json-report --json-report-file={json_report_path}"
        
        # Pytest will return exit code 1 if tests fail, which is normal.
        res = await self.sandbox.run_command(cmd)
        
        # Read the json result file
        cat_res = await self.sandbox.read_file(json_report_path)
        if not cat_res:
            print(f"⚠️ [TEST ORCHESTRATOR] Failed to read test report JSON. Output tracking broken. Raw stderr: {res.stderr}")
            if "ModuleNotFoundError" in res.stderr:
                 print("Hint: Module missing. Ensure PYTHONPATH or imports are correct inside sandbox.")
            return []
            
        try:
            report = json.loads(cat_res)
            results = []
            
            for test in report.get("tests", []):
                outcome = test.get("outcome", "failed")
                name = test.get("nodeid", "unknown_test")
                
                # Pytest-json-report timing is in seconds -> convert to ms
                setup_time = test.get("setup", {}).get("duration", 0)
                call_time = test.get("call", {}).get("duration", 0)
                teardown_time = test.get("teardown", {}).get("duration", 0)
                total_duration_ms = int((setup_time + call_time + teardown_time) * 1000)
                
                error_trace = None
                if outcome == "failed":
                    error_trace = test.get("call", {}).get("crash", {}).get("message", "")
                    if not error_trace:
                        error_trace = test.get("setup", {}).get("crash", {}).get("message", "Unknown error")
                        
                results.append(TestResult(
                    name=name,
                    status=outcome,
                    duration_ms=total_duration_ms,
                    error_trace=error_trace
                ))
            
            print(f"✅ [TEST ORCHESTRATOR] Completed test run. {len(results)} executed.")
            return results
        except json.JSONDecodeError:
            print(f"⚠️ [TEST ORCHESTRATOR] Invalid JSON in test report.")
            return []

    async def build_context_map(self) -> bool:
        """
        Runs full test suite with coverage and context tracking, then pipes JSON directly into the Context Compiler layer.
        """
        ready = await self._ensure_test_env()
        if not ready:
            return False
            
        print("🧬 [TEST ORCHESTRATOR] Building Architectural Context Map via Coverage...")
        
        # 1. Run tests with coverage context tracking
        run_cmd = "python3 -m pytest . --cov=/workspace --cov-context=test"
        await self.sandbox.run_command(run_cmd)
        
        # 2. Extract context to coverage.json
        json_cmd = "python3 -m coverage json -o /workspace/coverage.json --show-contexts"
        await self.sandbox.run_command(json_cmd)
        
        # 3. Read it out of Docker
        cov_out = await self.sandbox.read_file("/workspace/coverage.json")
        if not cov_out:
            print("⚠️ [TEST ORCHESTRATOR] Coverage mapping failed. JSON not found.")
            return False
            
        # 4. Synchronize memory
        context_compiler.parse_coverage_json(cov_out)
        return True
