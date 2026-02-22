from typing import Dict, Optional
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
        
        self.sandbox = DockerEnvironment(container_name=container_name)
        # Point the sandbox directly at the correct volume root
        self.sandbox.workspace_dir = root_path

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
