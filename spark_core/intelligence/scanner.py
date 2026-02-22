import ast
import os
import time
from typing import Optional, List, Set, Dict

from sandbox.docker_env import DockerEnvironment
from intelligence.graph import CodeGraph, CodeNode, CodeEdge
from intelligence.cycle_detector import detect_cycles

class PythonGraphBuilder(ast.NodeVisitor):
    def __init__(self, file_path: str, module_name: str, graph: CodeGraph):
        self.file_path = file_path
        self.module_name = module_name
        self.graph = graph

        self.current_class = None
        self.current_function = None
        self.imports_map: Dict[str, str] = {}  # alias -> real name

        # Add module node
        self.graph.add_node(CodeNode(
            id=self.module_name,
            type="module",
            path=self.file_path,
            signature="",
            start_line=1,
            end_line=1
        ))

    def _get_current_context(self) -> str:
        if self.current_function:
            return f"{self.module_name}.{self.current_class}.{self.current_function}" if self.current_class else f"{self.module_name}.{self.current_function}"
        if self.current_class:
            return f"{self.module_name}.{self.current_class}"
        return self.module_name

    def visit_Import(self, node: ast.Import):
        ctx = self._get_current_context()
        for alias in node.names:
            self.imports_map[alias.asname or alias.name] = alias.name
            self.graph.add_edge(source=ctx, target=alias.name, relation="imports")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        ctx = self._get_current_context()
        module = node.module or ""
        for alias in node.names:
            full_name = f"{module}.{alias.name}" if module else alias.name
            self.imports_map[alias.asname or alias.name] = full_name
            self.graph.add_edge(source=ctx, target=full_name, relation="imports")
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef):
        prev_class = self.current_class
        self.current_class = node.name

        class_id = self._get_current_context()
        self.graph.add_node(CodeNode(
            id=class_id,
            type="class",
            path=self.file_path,
            signature=f"class {node.name}",
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno
        ))
        
        for base in node.bases:
            if isinstance(base, ast.Name):
                target = self.imports_map.get(base.id, base.id)
                self.graph.add_edge(source=class_id, target=target, relation="inherits")

        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node: ast.FunctionDef):
        prev_func = self.current_function
        self.current_function = node.name

        func_id = self._get_current_context()
        args = [arg.arg for arg in node.args.args]
        sig = f"def {node.name}({', '.join(args)})"

        self.graph.add_node(CodeNode(
            id=func_id,
            type="function",
            path=self.file_path,
            signature=sig,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno
        ))

        self.generic_visit(node)
        self.current_function = prev_func

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        prev_func = self.current_function
        self.current_function = node.name

        func_id = self._get_current_context()
        args = [arg.arg for arg in node.args.args]
        sig = f"async def {node.name}({', '.join(args)})"

        self.graph.add_node(CodeNode(
            id=func_id,
            type="function",
            path=self.file_path,
            signature=sig,
            start_line=node.lineno,
            end_line=node.end_lineno or node.lineno
        ))

        self.generic_visit(node)
        self.current_function = prev_func

    def visit_Call(self, node: ast.Call):
        ctx = self._get_current_context()
        
        target = ""
        if isinstance(node.func, ast.Name):
            target = self.imports_map.get(node.func.id, node.func.id)
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                base = self.imports_map.get(node.func.value.id, node.func.value.id)
                target = f"{base}.{node.func.attr}"
                
        if target:
            self.graph.add_edge(source=ctx, target=target, relation="calls")

        self.generic_visit(node)


class WorkspaceScanner:
    def __init__(self, sandbox: DockerEnvironment, graph: CodeGraph):
        self.sandbox = sandbox
        self.graph = graph

    async def scan_workspace(self) -> dict:
        print("🧠 [SCANNER] Initiating host-fast workspace analysis...")
        
        self.graph.clear()
        
        root_dir = self.sandbox.workspace_dir
        if not root_dir or not os.path.exists(root_dir):
            print(f"⚠️ [SCANNER] Workspace dir not found: {root_dir}")
            return {"error": "Workspace directory not found on host."}
            
        py_files = []
        for dirpath, _, filenames in os.walk(root_dir):
            if "node_modules" in dirpath or ".git" in dirpath or "site-packages" in dirpath or "__pycache__" in dirpath:
                continue
            for f in filenames:
                if f.endswith(".py"):
                    py_files.append(os.path.join(dirpath, f))
                    
        print(f"🧠 [SCANNER] Found {len(py_files)} Python files to analyze on host.")
        
        for file_path in py_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    code_content = f.read()
            except Exception as e:
                print(f"⚠️ [SCANNER] Failed to read {file_path}: {e}")
                continue
                
            rel_path = os.path.relpath(file_path, root_dir)
            module_name = rel_path.replace(os.sep, ".").replace(".py", "")
            
            try:
                tree = ast.parse(code_content, filename=file_path)
                builder = PythonGraphBuilder(file_path=file_path, module_name=module_name, graph=self.graph)
                builder.visit(tree)
            except Exception as e:
                print(f"⚠️ [SCANNER] AST Parse Error on {file_path}: {e}")
                
        # Calculate cycles
        graph_dict = {
            node_id: self.graph.get_dependencies(node_id) 
            for node_id in self.graph.nodes
        }
        cycles = detect_cycles(graph_dict)
        
        # We also need to update this project's state.
        # But wait, self.sandbox.state_hook exists! (It's a UnifiedState)
        st = self.sandbox.state_hook.get_state()
        metrics = st.get("metrics", {})
        metrics["circular_dependencies"] = cycles
        self.sandbox.state_hook.update("metrics", metrics)
        
        print(f"✅ [SCANNER] Workspace indexed. Nodes: {len(self.graph.nodes)}, Edges: {len(self.graph.edges)}. Cycles: {cycles}")
        return self.graph.to_dict()
