from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable


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
        safe_parallel_tools = {
            "get_time",
            "web_search",
            "system_monitor",
            "get_weather",
            "read_clipboard",
        }

        def _run_tool(step_name: str, step_arg: str) -> tuple[str, str]:
            tool_fn = self.tools.get(step_name)
            if not tool_fn:
                raise KeyError(step_name)
            result = tool_fn(step_arg)
            return step_name, str(result)

        pending_batch: list[tuple[str, str]] = []

        def _flush_batch() -> bool:
            nonlocal pending_batch
            if not pending_batch:
                return True

            batch = pending_batch
            pending_batch = []
            if len(batch) == 1:
                step_name, step_arg = batch[0]
                try:
                    tool_name, result = _run_tool(step_name, step_arg)
                    task.results.append(f"{tool_name}: {result}")
                    log.info("Tool %s(%r) -> %s", tool_name, step_arg, result[:120])
                    return True
                except Exception as exc:
                    log.error("Tool %s failed: %s", step_name, exc)
                    task.status = "blocked"
                    return False

            with ThreadPoolExecutor(max_workers=min(len(batch), 4)) as executor:
                futures = {
                    executor.submit(_run_tool, step_name, step_arg): (index, step_name, step_arg)
                    for index, (step_name, step_arg) in enumerate(batch)
                }
                ordered_results: list[tuple[int, str, str]] = []
                for future in as_completed(futures):
                    index, step_name, step_arg = futures[future]
                    try:
                        tool_name, result = future.result()
                        ordered_results.append((index, tool_name, result))
                    except Exception as exc:
                        log.error("Tool %s failed: %s", step_name, exc)
                        task.status = "blocked"
                        return False

            for _, tool_name, result in sorted(ordered_results, key=lambda item: item[0]):
                task.results.append(f"{tool_name}: {result}")
                log.info("Tool %s -> %s", tool_name, result[:120])
            return True

        for step in task.steps:
            if ":" in step:
                tool_name, arg = step.split(":", 1)
            else:
                tool_name, arg = step, ""

            tool_name = tool_name.strip()
            arg = arg.strip()

            if tool_name == "respond":
                if not _flush_batch():
                    break
                result = self.llm(
                    f"Goal: {task.goal}\nPrevious results: {task.results}\nRespond to the user."
                )
                task.results.append(result)
                continue

            if tool_name in safe_parallel_tools:
                pending_batch.append((tool_name, arg))
                continue

            if not _flush_batch():
                break

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

        if task.status == "running" and not _flush_batch():
            pass

        if task.status == "running":
            task.status = "done"
        return task


TaskQueue = TaskPlanner


async def spark_plan_and_execute(
    goal: str,
    llm_call: Callable[[str], str],
    tool_executor: Callable[[str, str], Awaitable[str]],
    available_tools: list[str],
    stream_sink: Callable[[str, dict[str, Any]], None] | None = None,
    max_steps: int = 5,
) -> dict[str, Any]:
    """Break a goal into bounded steps and execute them sequentially."""
    prompt = (
        "Break this goal into up to 5 concrete steps. "
        f"Use only these tools when appropriate: {available_tools}. "
        'Reply only as JSON: {"steps": ["tool:arg", ...], "summary": "..."}\n\n'
        f"Goal: {goal}"
    )
    raw = llm_call(prompt)

    steps: list[str] = []
    summary = ""
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            maybe_steps = parsed.get("steps", [])
            if isinstance(maybe_steps, list):
                steps = [str(step) for step in maybe_steps if str(step).strip()]
            summary = str(parsed.get("summary", "")).strip()
    except Exception:
        steps = []

    if not steps:
        steps = [f"respond:{goal}"]

    steps = steps[:max_steps]
    results: list[str] = []

    for step in steps:
        if ":" in step:
            tool_name, arg = step.split(":", 1)
        else:
            tool_name, arg = step, ""
        tool_name = tool_name.strip()
        arg = arg.strip()

        if stream_sink:
            stream_sink("plan_step", {"tool": tool_name, "arg": arg})

        if tool_name == "respond":
            results.append(arg or goal)
            continue

        try:
            result = await tool_executor(tool_name, arg)
            results.append(f"{tool_name}: {result}")
            if stream_sink:
                stream_sink("plan_result", {"tool": tool_name, "result": result})
        except Exception as exc:
            failure = f"{tool_name}: ERROR {exc}"
            results.append(failure)
            if stream_sink:
                stream_sink("plan_result", {"tool": tool_name, "result": failure})
            break

    if not summary:
        summary = results[-1] if results else "No execution results were produced."

    return {"goal": goal, "steps": steps, "results": results, "summary": summary}