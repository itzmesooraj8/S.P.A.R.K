from typing import Dict, Optional, Any
import time
from system.state import UnifiedState
from sandbox.docker_env import DockerEnvironment
import hashlib

class ProjectContext:
    def __init__(self, project_id: str, root_path: str):
        self.project_id = project_id
        self.root_path = root_path
        
        # Dedicated state isolation per-project
        self.state = UnifiedState()
        
        # Consistent, identifiable container naming based on hash to avoid filesystem issues
        safe_hash = hashlib.md5(project_id.encode('utf-8')).hexdigest()[:8]
        container_name = f"spark_sandbox_{safe_hash}"
        
        self.sandbox = DockerEnvironment(container_name=container_name, state_hook=self.state)
        # Point the sandbox directly at the correct volume root
        self.sandbox.workspace_dir = root_path

    def export_snapshot(self) -> Dict[str, Any]:
        """Provides a safe, bounded, read-only analytical snapshot of this project space."""
        st = self.state.get_state()
        
        # Safe extraction layers to avoid exceptions on incomplete mappings
        cg = st.get('code_graph', {})
        nodes = cg.get('nodes', [])
        edges = cg.get('edges', [])
        
        # Explicit Bounding Counters
        num_files = sum(1 for n in nodes if n.get('type') == 'file')
        num_funcs = sum(1 for n in nodes if n.get('type') == 'function')
        num_classes = sum(1 for n in nodes if n.get('type') == 'class')
        
        # Mutation bounds
        mutation_log = st.get('mutation_log', [])
        now = time.time()
        recent_mut = [m for m in mutation_log if now - m.get('timestamp', 0) < 86400]
        files_mod = list(set([m.get("target_file", "") for m in mutation_log]))
        
        sandbox_state = st.get("sandbox_state", {})
        last_cmd = str(sandbox_state.get("last_cmd", ""))
        
        metrics = st.get("metrics", {})
        
        # Enforce exact bounding constraints
        return {
            "snapshot_schema_version": "1.0",
            "project_id": str(self.project_id)[:50],
            "timestamp": now,
            
            "graph": {
                "total_files": num_files,
                "total_functions": num_funcs,
                "total_classes": num_classes,
                "dependency_edges": len(edges),
                "circular_dependencies": metrics.get("circular_dependencies", 0),
                "largest_file_lines": 0  # To be fed from AST metrics over time
            },
            
            "structure_digest": {
                # Bound to max 20, derived from file structure
                "top_level_dirs": [],  
                "primary_languages": ["python", "typescript"] if num_files > 0 else [], 
                "frameworks_detected": [],  
            },
            
            "execution_profile": {
                "sandbox_active": sandbox_state.get("is_running", False),
                "last_command": last_cmd[:120] if last_cmd else None,
                "last_exit_code": sandbox_state.get("last_exit_code", None),
                "avg_exec_time_ms": 0.0,
            },
            
            "mutation_profile": {
                "total_mutations": len(mutation_log),
                "recent_mutations_24h": len(recent_mut),
                "files_modified_count": len(files_mod),
                "most_modified_files": [f.split('/')[-1][:50] for f in files_mod][:5],
            },
            
            "risk_profile": {
                "lint_errors": metrics.get("lint_errors", 0),
                "type_errors": metrics.get("type_errors", 0),
                "known_vulnerabilities": 0,
                "unsafe_patterns_detected": 0,
            },
            
            "resource_profile": {
                "estimated_loc": num_files * 150,  # Estimator
                "container_memory_mb": None, # Will be fetched dynamically
                "container_cpu_percent": None,
            }
        }

class MultiProjectRegistry:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MultiProjectRegistry, cls).__new__(cls)
            cls._instance._init_registry()
        return cls._instance

    def _init_registry(self):
        self.active_projects: Dict[str, ProjectContext] = {}
        self.current_focus: Optional[str] = None

    def load_project(self, project_id: str, path: str) -> ProjectContext:
        """Loads a project namespace and mounts its execution bounds."""
        if project_id not in self.active_projects:
            context = ProjectContext(project_id, path)
            self.active_projects[project_id] = context
            print(f"🧬 [REGISTRY] Initialized Project Context: {project_id}")
            
        self.current_focus = project_id
        return self.active_projects[project_id]

    def get_active(self) -> Optional[ProjectContext]:
        """Returns the currently active project execution space."""
        if not self.current_focus:
            return None
        return self.active_projects.get(self.current_focus)

    def switch_focus(self, project_id: str):
        if project_id in self.active_projects:
            self.current_focus = project_id
            print(f"🔄 [REGISTRY] Switched focus to: {project_id}")
            
            # Auto-hook the websocket manager to the new State instance
            from ws.manager import ws_manager
            # Flush existing hooks (in a real system we'd manage a cleanly detached list)
            ctx = self.active_projects[project_id]
            
            # Fire an immediate initialization frame 
            ctx.state.update("project_focus", project_id)

project_registry = MultiProjectRegistry()
