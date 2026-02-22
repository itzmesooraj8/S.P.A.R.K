import json
import os
import time
from typing import Dict, Any, List, Set, Optional
from intelligence.graph import CodeGraph
from system.state import unified_state

CONTEXT_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "memory", "context_map.json")

class ContextCompiler:
    """
    Sovereign Dev Kernel v3 Layer.
    Maps explicitly executed code back to the test assertions that cover them.
    Allows for contextual risk modeling and selective test cascading without static inference.
    """
    def __init__(self, graph: CodeGraph):
        self.graph = graph
        self.node_to_tests: Dict[str, Set[str]] = {}
        self.test_to_nodes: Dict[str, Set[str]] = {}
        self._load()

    def _load(self):
        if not os.path.exists(CONTEXT_FILE):
            return
        try:
            with open(CONTEXT_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.node_to_tests = {k: set(v) for k, v in data.get("node_to_tests", {}).items()}
                self.test_to_nodes = {k: set(v) for k, v in data.get("test_to_nodes", {}).items()}
        except Exception as e:
            print(f"⚠️ [CONTEXT COMPILER] Failed to load context map: {e}")

    def _save(self):
        os.makedirs(os.path.dirname(CONTEXT_FILE), exist_ok=True)
        data = {
            "node_to_tests": {k: list(v) for k, v in self.node_to_tests.items()},
            "test_to_nodes": {k: list(v) for k, v in self.test_to_nodes.items()}
        }
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
        unified_state.update("context_map", data)

    def parse_coverage_json(self, coverage_text: str):
        """
        Ingests the pytest-cov generated `coverage.json` created via `--cov-context=test`.
        Determines line overlap dynamically mapping Test Execution to Structural Nodes.
        """
        try:
            cov_data = json.loads(coverage_text)
        except json.JSONDecodeError as e:
            print(f"⚠️ [CONTEXT COMPILER] Failed to parse coverage JSON: {e}")
            return
            
        files_map = cov_data.get("files", {})
        
        # We start fresh on each full architectural remap
        self.node_to_tests.clear()
        self.test_to_nodes.clear()
        
        print(f"🧬 [CONTEXT COMPILER] Cross-referencing {len(files_map)} covered files against Graph...")

        for file_path, file_data in files_map.items():
            # Coverage path normalization matching graph
            # Nodes store fully qualified absolute paths or relative workspace paths.
            # Convert file_path to workspace relative
            search_path = file_path
            if search_path.startswith("/workspace/"):
                search_path = search_path[len("/workspace/"):]
            if search_path.startswith("./"):
                search_path = search_path[2:]

            # Retrieve CodeNodes targeting this file
            file_nodes = [n for n in self.graph.nodes.values() if search_path in n.path.replace("\\", "/")]
            
            contexts = file_data.get("contexts", {})
            for line_str, tests in contexts.items():
                line_idx = int(line_str)
                
                # Check which structural node spans this line.
                hit_node = None
                for n in file_nodes:
                    if n.start_line <= line_idx <= n.end_line:
                        # Map to the tightest node if multiple overlap (e.g. class vs function)
                        # The one with the smaller span is the more specific node.
                        if hit_node is None:
                            hit_node = n
                        else:
                            span1 = hit_node.end_line - hit_node.start_line
                            span2 = n.end_line - n.start_line
                            if span2 < span1:
                                hit_node = n

                if hit_node:
                    for t in tests:
                        # Some tests may include parameterized info, split by | if necessary but raw works.
                        test_str = t.split("|")[0]
                        if not test_str: 
                            continue # Empty means no test context (top level load)

                        if hit_node.id not in self.node_to_tests:
                            self.node_to_tests[hit_node.id] = set()
                        self.node_to_tests[hit_node.id].add(test_str)
                        
                        if test_str not in self.test_to_nodes:
                            self.test_to_nodes[test_str] = set()
                        self.test_to_nodes[test_str].add(hit_node.id)

        self._save()
        mapped_nodes = len(self.node_to_tests)
        mapped_tests = len(self.test_to_nodes)
        print(f"✅ [CONTEXT COMPILER] Synchronized: {mapped_nodes} nodes <-> {mapped_tests} tests.")

    def get_tests_for_node(self, target_node: str) -> List[str]:
        return sorted(list(self.node_to_tests.get(target_node, set())))

    def get_nodes_for_test(self, test_id: str) -> List[str]:
        return sorted(list(self.test_to_nodes.get(test_id, set())))

    def map_downstream_impact(self, failing_test_id: str) -> List[str]:
        """
        If a test fails natively, everything that test covers theoretically holds a piece of the risk.
        This provides cascading contextual risk boundaries.
        """
        return self.get_nodes_for_test(failing_test_id)

    def calculate_contextual_risk_modifier(self, target_node: str) -> float:
        """
        If we mutate `target_node`, which other nodes share test coverage boundaries with it?
        If `target_node` is highly entangled, its contextual risk multiplier explodes.
        """
        tests = self.get_tests_for_node(target_node)
        if not tests:
            return 1.0 # Base modifier
            
        entangled_nodes = set()
        for t in tests:
            for n in self.get_nodes_for_test(t):
                if n != target_node:
                    entangled_nodes.add(n)
                    
        # Every uniquely entangled node adds +0.02 multiplier
        multiplier = 1.0 + (len(entangled_nodes) * 0.02)
        return min(multiplier, 2.0) # Cap context blast radius scaling at 2x

from intelligence.graph import CodeGraph
from tools.intelligence import shared_code_graph

context_compiler = ContextCompiler(graph=shared_code_graph)
