from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Callable


log = logging.getLogger("spark.planner")


@dataclass
class Task:
    goal: str
    steps: list[str] = field(default_factory=list)
    results: list[str] = field(default_factory=list)
    status: str = "pending"


class TaskPlanner:
    def __init__(self, llm_call: Callable[[str], str], tools: dict[str, Callable[[str], str]]):
        self.llm = llm_call
        self.tools = tools

    def plan(self, goal: str) -> Task:
        task = Task(goal=goal)
        decompose_prompt = (
            "Break this goal into 2-5 concrete steps. "
            f"Each step must be one of: {list(self.tools.keys())} or 'respond'.\n"
            'Reply only as JSON: {"steps": ["tool:arg", ...]}\n\n'
            f"Goal: {goal}"
        )
        raw = self.llm(decompose_prompt)
        try:
            parsed = json.loads(raw)
            steps = parsed.get("steps", [])
            if isinstance(steps, list):
                task.steps = [str(step) for step in steps if str(step).strip()]
        except Exception:
            task.steps = []

        if not task.steps:
            task.steps = [f"respond:{goal}"]
        return task

    def execute(self, task: Task) -> Task:
        task.status = "running"

        for step in task.steps:
            if ":" in step:
                tool_name, arg = step.split(":", 1)
            else:
                tool_name, arg = step, ""

            tool_name = tool_name.strip()
            arg = arg.strip()

            if tool_name == "respond":
                result = self.llm(
                    f"Goal: {task.goal}\nPrevious results: {task.results}\nRespond to the user."
                )
                task.results.append(result)
                continue

            tool_fn = self.tools.get(tool_name)
            if not tool_fn:
                log.warning("Unknown tool: %s", tool_name)
                task.status = "blocked"
                break

            try:
                result = tool_fn(arg)
                task.results.append(f"{tool_name}: {result}")
                log.info("Tool %s(%r) -> %s", tool_name, arg, str(result)[:120])
            except Exception as exc:
                log.error("Tool %s failed: %s", tool_name, exc)
                task.status = "blocked"
                break

        if task.status == "running":
            task.status = "done"
        return task


TaskQueue = TaskPlanner