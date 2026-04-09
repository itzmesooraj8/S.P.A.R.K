import importlib.util
import os
import sys
from typing import Dict, Type
from .base import Skill

class SkillRegistry:
    def __init__(self):
        self.skills: Dict[str, Skill] = {}

    def register(self, skill_class: Type[Skill]):
        skill_instance = skill_class()
        self.skills[skill_instance.name] = skill_instance
        print(f"🧩 [SkillRegistry] Builtin Skill registered: {skill_instance.name}")

    def load_from_file(self, file_path: str):
        if not file_path.endswith(".py"):
            return
        module_name = os.path.basename(file_path)[:-3]
        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            try:
                spec.loader.exec_module(module)
                # Find classes that inherit from Skill
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if isinstance(attr, type) and issubclass(attr, Skill) and attr is not Skill:
                        skill_instance = attr()
                        self.skills[skill_instance.name] = skill_instance
                        print(f"🔥 [SkillRegistry] Hot-loaded Skill: {skill_instance.name}")
            except Exception as e:
                print(f"⚠️ [SkillRegistry] Error evaluating {file_path}: {e}")

    def get_skill(self, name: str) -> Skill:
        return self.skills.get(name)

# Global Registry
skill_registry = SkillRegistry()
