from __future__ import annotations

import json
import re
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from config import LLM_HOST, LLM_MODEL
from core.planner import TaskPlanner
from core.memory_loop import write_turn
from core.tools import SparkTools
from core.orchestrator.agent_bus import get_agent_bus
from core.orchestrator.router import get_orchestrator_router
from security.audit import record_audit
from security.action_guard import guard_tool_function
from security.content_sanitizer import sanitize_for_llm
from security.intent_validator import validate_intent_text
from tools.file_ops import search_and_open_file
from tools.media import control_media
from tools.sysmon import get_system_health
from tools.weather import get_weather
from tools.web_search import web_search_answer


router = APIRouter()

_tools = SparkTools()
_planner: TaskPlanner | None = None
_orchestrator = get_orchestrator_router()
_bus = get_agent_bus()
_task_status: dict[str, dict[str, Any]] = {}


class TaskRequest(BaseModel):
    goal: str = Field(min_length=1)


def _extract_goal_from_prompt(prompt: str) -> str:
    match = re.search(r"Goal:\s*(.+)$", prompt, flags=re.DOTALL)
    return match.group(1).strip() if match else prompt.strip()


def _local_plan(goal: str) -> str:
    text = goal.lower()
    steps: list[str] = []

    if any(word in text for word in ["search", "find", "look up", "summarize", "research"]):
        steps.append(f"web_search:{goal}")
    if any(word in text for word in ["open", "launch", "start", "run"]):
        steps.append("open_application:browser")
    if any(word in text for word in ["weather", "temperature"]):
        steps.append("get_weather:Palakkad")
    if not steps:
        steps.append(f"respond:{goal}")
    elif len(steps) == 1:
        steps.append(f"respond:{goal}")

    return json.dumps({"steps": steps[:5]})


def _local_response(prompt: str) -> str:
    goal = _extract_goal_from_prompt(prompt)
    if not goal:
        return "Task completed."
    return f"I have processed the goal: {goal}."


def _llm_call(prompt: str) -> str:
    if 'Break this goal into' in prompt:
        try:
            response = httpx.post(
                f"{LLM_HOST}/api/generate",
                json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
                timeout=3.0,
            )
            response.raise_for_status()
            content = response.json().get("response", "").strip()
            if content:
                return content
        except Exception:
            pass
        return _local_plan(_extract_goal_from_prompt(prompt))

    try:
        response = httpx.post(
            f"{LLM_HOST}/api/generate",
            json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
            timeout=3.0,
        )
        response.raise_for_status()
        content = response.json().get("response", "").strip()
        if content:
            return content
    except Exception:
        pass

    return _local_response(prompt)


def _tool_map() -> dict[str, Any]:
    return {
        "open_website": guard_tool_function("open_website", _tools.open_website, source="task", risk="medium"),
        "open_application": guard_tool_function("open_application", _tools.open_application, source="task", risk="medium"),
        "read_clipboard": guard_tool_function("read_clipboard", lambda _: _tools.read_clipboard(), source="task", risk="low"),
        "write_clipboard": guard_tool_function("write_clipboard", _tools.write_clipboard, source="task", risk="medium"),
        "get_time": guard_tool_function("get_time", lambda _: _tools.get_time(), source="task", risk="low"),
        "web_search": guard_tool_function("web_search", web_search_answer, source="task", risk="low"),
        "system_monitor": guard_tool_function("system_monitor", lambda _: get_system_health(), source="task", risk="low"),
        "get_weather": guard_tool_function("get_weather", lambda arg: get_weather(arg or "Palakkad"), source="task", risk="low"),
        "file_search": guard_tool_function("file_search", search_and_open_file, source="task", risk="medium"),
        "media_control": guard_tool_function("media_control", control_media, source="task", risk="low"),
    }


def get_planner() -> TaskPlanner:
    global _planner
    if _planner is None:
        _planner = TaskPlanner(_llm_call, _tool_map())
    return _planner


def run_task_sync(goal: str) -> dict[str, Any]:
    task_id = uuid.uuid4().hex
    validation = validate_intent_text(goal)
    sanitized_goal = sanitize_for_llm(validation.cleaned_text or goal)
    if not validation.allowed:
        blocked = {
            "task_id": task_id,
            "goal": goal,
            "status": "blocked",
            "steps": [],
            "results": ["Security policy blocked the requested goal."],
            "orchestration": {},
        }
        _task_status[task_id] = blocked
        record_audit("task_goal_blocked", {"task_id": task_id, "goal": goal, "score": validation.score, "reasons": list(validation.reasons)})
        return blocked

    _task_status[task_id] = {"task_id": task_id, "goal": sanitized_goal, "status": "running", "steps": [], "results": []}
    try:
        orchestration = _orchestrator.route(sanitized_goal, {"task_id": task_id, "source": "planner"})
        _bus.emit("execution_started", {"task_id": task_id, "goal": sanitized_goal, "route": orchestration})
        write_turn("user", sanitized_goal, metadata={"source": "planner", "task_id": task_id})
    except Exception:
        orchestration = {}

    try:
        planner = get_planner()
        task = planner.plan(sanitized_goal)
        task = planner.execute(task)
        result_text = "\n".join(task.results) if task.results else task.status
        try:
            write_turn(
                "assistant",
                result_text,
                metadata={"source": "planner", "task_id": task_id, "goal": task.goal},
            )
        except Exception:
            pass

        result = {
            "task_id": task_id,
            "goal": task.goal,
            "status": task.status,
            "steps": task.steps,
            "results": task.results,
            "orchestration": orchestration,
        }
        _task_status[task_id] = result
        _bus.emit("execution_completed", {"task_id": task_id, "goal": task.goal, "status": task.status, "steps": task.steps})
        return result
    except Exception as exc:
        failed = {
            "task_id": task_id,
            "goal": sanitized_goal,
            "status": "blocked",
            "steps": [],
            "results": [str(exc)],
            "orchestration": orchestration,
        }
        _task_status[task_id] = failed
        _bus.emit("execution_failed", {"task_id": task_id, "goal": sanitized_goal, "error": str(exc)})
        return failed


@router.post("/api/task")
@router.post("/api/task/execute")
async def execute_task(request: TaskRequest, background_tasks: BackgroundTasks):
    try:
        task_id = uuid.uuid4().hex
        _task_status[task_id] = {"task_id": task_id, "goal": sanitize_for_llm(request.goal), "status": "queued", "steps": [], "results": []}

        def _run_with_task_id() -> None:
            _task_status[task_id] = {"task_id": task_id, "goal": sanitize_for_llm(request.goal), "status": "running", "steps": [], "results": []}
            try:
                result = run_task_sync(request.goal)
                result["task_id"] = task_id
                _task_status[task_id] = result
            except Exception as exc:
                _task_status[task_id] = {
                    "task_id": task_id,
                    "goal": sanitize_for_llm(request.goal),
                    "status": "blocked",
                    "steps": [],
                    "results": [str(exc)],
                    "orchestration": {},
                }

        background_tasks.add_task(_run_with_task_id)
        return {
            "task_id": task_id,
            "goal": request.goal,
            "status": "queued",
            "steps": [],
            "results": [],
        }
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@router.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    task = _task_status.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task