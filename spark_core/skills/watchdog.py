import os
import asyncio
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    from spark_core.skills.registry import skill_registry
except ImportError:
    from skills.registry import skill_registry

_SKILL_CORE_FILES = {"__init__.py", "base.py", "registry.py", "watchdog.py"}

class SkillReloadHandler(FileSystemEventHandler):
    def on_modified(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return
        if os.path.basename(event.src_path) in _SKILL_CORE_FILES:
            return
        print(f"🔄 [SkillWatchdog] Detected modification. Reloading: {os.path.basename(event.src_path)}")
        skill_registry.load_from_file(event.src_path)
        
    def on_created(self, event):
        if event.is_directory or not event.src_path.endswith('.py'):
            return
        if os.path.basename(event.src_path) in _SKILL_CORE_FILES:
            return
        print(f"✨ [SkillWatchdog] Detected new skill: {os.path.basename(event.src_path)}")
        skill_registry.load_from_file(event.src_path)

class SkillWatchdog:
    def __init__(self, skills_dir: str):
        self.skills_dir = skills_dir
        self.observer = Observer()

    def start(self):
        if not os.path.exists(self.skills_dir):
            os.makedirs(self.skills_dir, exist_ok=True)
            
        # Initial load load
        for f in os.listdir(self.skills_dir):
            if f.endswith(".py") and f not in _SKILL_CORE_FILES:
                skill_registry.load_from_file(os.path.join(self.skills_dir, f))

        event_handler = SkillReloadHandler()
        self.observer.schedule(event_handler, self.skills_dir, recursive=False)
        self.observer.start()
        print(f"👁️ [SkillWatchdog] Active on hot-reload directory: {self.skills_dir}")

    def stop(self):
        self.observer.stop()
        self.observer.join()
