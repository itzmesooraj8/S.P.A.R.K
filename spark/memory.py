from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Task:
    id: str
    prompt: str
    source: str = "self"
    due_at: float = 0.0


class SparkMemory:
    def __init__(self, config: dict[str, Any]):
        memory_config = config.get("memory", {}) if isinstance(config, dict) else {}
        self.turn_log_path = Path(memory_config.get("turn_log_path", "spark_dev_memory/turns.jsonl"))
        self.task_queue_path = Path(memory_config.get("task_queue_path", "spark_dev_memory/task_queue.json"))
        self.user_model_path = Path(memory_config.get("user_model_path", "spark_dev_memory/user_model.json"))
        self.system_prompt_path = Path(memory_config.get("system_prompt_path", "spark_dev_memory/system_prompt.txt"))
        self.defaults = (config.get("user_model_defaults", {}) if isinstance(config, dict) else {}) or {}
        self.turn_log_path.parent.mkdir(parents=True, exist_ok=True)
        self.task_queue_path.parent.mkdir(parents=True, exist_ok=True)
        self.user_model_path.parent.mkdir(parents=True, exist_ok=True)
        self.system_prompt_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_user_model()

    def _read_json(self, path: Path, default: Any) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return default

    def _write_json(self, path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def _ensure_user_model(self) -> dict[str, Any]:
        model = self._read_json(self.user_model_path, {})
        if not isinstance(model, dict):
            model = {}
        if not model:
            model = {"sooraj": dict(self.defaults)}
            self._write_json(self.user_model_path, model)
        return model

    def _read_task_queue(self) -> list[dict[str, Any]]:
        queue = self._read_json(self.task_queue_path, [])
        return queue if isinstance(queue, list) else []

    def _write_task_queue(self, queue: list[dict[str, Any]]) -> None:
        self._write_json(self.task_queue_path, queue)

    def get_next_task(self) -> dict[str, Any] | None:
        queue = self._read_task_queue()
        if not queue:
            return None
        now = time.time()
        ready_index = None
        for index, task in enumerate(queue):
            due_at = float(task.get("due_at", 0.0) or 0.0)
            if due_at <= now:
                ready_index = index
                break
        if ready_index is None:
            return None
        task = queue.pop(ready_index)
        self._write_task_queue(queue)
        return task

    def queue_tasks(self, tasks: list[dict[str, Any]] | list[Task]) -> list[dict[str, Any]]:
        queue = self._read_task_queue()
        now = time.time()
        normalized: list[dict[str, Any]] = []
        for task in tasks:
            if isinstance(task, Task):
                normalized.append({"id": task.id, "prompt": task.prompt, "source": task.source, "due_at": task.due_at or now})
            elif isinstance(task, dict) and task.get("prompt"):
                normalized.append({
                    "id": str(task.get("id") or uuid.uuid4().hex),
                    "prompt": str(task.get("prompt", "")),
                    "source": str(task.get("source", "self")),
                    "due_at": float(task.get("due_at", now) or now),
                })
        if normalized:
            queue.extend(normalized)
            self._write_task_queue(queue)
        return normalized

    def log_outcome(self, task: dict[str, Any] | str, result: Any) -> dict[str, Any]:
        prompt = task.get("prompt", "") if isinstance(task, dict) else str(task)
        entry = {
            "id": uuid.uuid4().hex,
            "ts": time.time(),
            "task": prompt,
            "result": self._stringify(result),
        }
        with self.turn_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        self._update_user_model(prompt, entry["result"])
        return entry

    def recent_interactions(self, limit: int = 50) -> list[dict[str, Any]]:
        if not self.turn_log_path.exists():
            return []
        lines = [line.strip() for line in self.turn_log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        recent: list[dict[str, Any]] = []
        for line in lines[-limit:]:
            try:
                recent.append(json.loads(line))
            except Exception:
                continue
        return recent

    def _stringify(self, value: Any) -> str:
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)

    def _update_user_model(self, prompt: str, result: str) -> None:
        model = self._ensure_user_model()
        profile = model.setdefault("sooraj", dict(self.defaults))
        projects = profile.setdefault("current_projects", [])
        matches = re.findall(r"\bSPARK\b|\bSolo Level app\b|\b[\w-]+\b", prompt, flags=re.IGNORECASE)
        for match in matches:
            normalized = match.strip()
            if len(normalized) > 2 and normalized not in projects:
                if len(projects) < 10:
                    projects.append(normalized)
        if len(result) < 120 and any(word in result.lower() for word in ["failed", "error", "unable"]):
            profile["last_negative_feedback"] = result[:200]
        self._write_json(self.user_model_path, model)

    def load_system_prompt(self) -> str:
        if self.system_prompt_path.exists():
            return self.system_prompt_path.read_text(encoding="utf-8")
        return "You are SPARK, a proactive autonomous assistant. Be concise, accurate, and stateful."

    def save_system_prompt(self, prompt: str) -> None:
        self.system_prompt_path.write_text(prompt.strip() + "\n", encoding="utf-8")
