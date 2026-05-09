from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()


class TaskCreateRequest(BaseModel):
    title: str = Field(min_length=1)
    description: str | None = None
    status: str = "open"
    priority: int = 3
    due_date: int | None = None
    tags: list[str] = []
    recurring: str | None = None
    meta: dict[str, Any] | None = None


class TaskUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    priority: int | None = None
    due_date: int | None = None
    tags: list[str] | None = None
    recurring: str | None = None
    meta: dict[str, Any] | None = None


class BriefingCreateRequest(BaseModel):
    content_text: str = Field(min_length=1)
    title: str | None = None
    content_audio_url: str | None = None
    mood: str | None = None
    tags: list[str] = []
    meta: dict[str, Any] | None = None


class BriefingUpdateRequest(BaseModel):
    title: str | None = None
    content_text: str | None = None
    content_audio_url: str | None = None
    mood: str | None = None
    tags: list[str] | None = None
    meta: dict[str, Any] | None = None


_TASKS: dict[str, dict[str, Any]] = {}
_TASK_HISTORY: list[dict[str, Any]] = []
_BRIEFINGS: dict[str, dict[str, Any]] = {}


def _now_ms() -> int:
    return int(time.time() * 1000)


def _task_list(offset: int = 0, limit: int = 100, status: str | None = None, priority: int | None = None) -> dict[str, Any]:
    tasks = list(_TASKS.values())
    if status:
        tasks = [task for task in tasks if task.get("status") == status]
    if priority is not None:
        tasks = [task for task in tasks if int(task.get("priority", 0)) == priority]
    total = len(tasks)
    return {"tasks": tasks[offset: offset + limit], "total": total, "offset": offset, "limit": limit}


@router.get("/personal/tasks")
async def list_tasks(status: str | None = None, priority: int | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    return _task_list(offset=offset, limit=max(1, limit), status=status, priority=priority)


@router.post("/personal/tasks")
async def create_task(request: TaskCreateRequest) -> dict[str, Any]:
    task_id = uuid.uuid4().hex
    now = _now_ms()
    task = {
        "id": task_id,
        "title": request.title,
        "description": request.description,
        "status": request.status,
        "priority": request.priority,
        "due_date": request.due_date,
        "tags": request.tags,
        "recurring": request.recurring,
        "created_at": now,
        "updated_at": now,
        "meta": request.meta or {},
    }
    _TASKS[task_id] = task
    return task


@router.get("/personal/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    task = _TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.put("/personal/tasks/{task_id}")
async def update_task(task_id: str, request: TaskUpdateRequest) -> dict[str, Any]:
    task = _TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    updated = task.copy()
    for field, value in request.model_dump(exclude_unset=True).items():
        updated[field] = value
    updated["updated_at"] = _now_ms()
    _TASKS[task_id] = updated
    return updated


@router.delete("/personal/tasks/{task_id}")
async def delete_task(task_id: str) -> dict[str, Any]:
    if task_id not in _TASKS:
        raise HTTPException(status_code=404, detail="task not found")
    del _TASKS[task_id]
    return {"status": "ok", "deleted": task_id}


@router.post("/personal/tasks/{task_id}/complete")
async def complete_task(task_id: str) -> dict[str, Any]:
    task = _TASKS.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="task not found")
    task = task.copy()
    task["status"] = "completed"
    task["updated_at"] = _now_ms()
    _TASKS[task_id] = task
    _TASK_HISTORY.append({
        "id": uuid.uuid4().hex,
        "original_task_id": task_id,
        "status_snapshot": task,
        "completed_at": _now_ms(),
        "duration_seconds": None,
        "meta": task.get("meta", {}),
    })
    return task


@router.get("/personal/tasks/history")
async def task_history(task_id: str | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    items = _TASK_HISTORY
    if task_id:
        items = [item for item in items if item.get("original_task_id") == task_id]
    total = len(items)
    return {"history": items[offset: offset + max(1, limit)], "total": total, "offset": offset, "limit": limit}


@router.get("/personal/briefings")
async def list_briefings(mood: str | None = None, limit: int = 100, offset: int = 0) -> dict[str, Any]:
    briefings = list(_BRIEFINGS.values())
    if mood:
        briefings = [briefing for briefing in briefings if briefing.get("mood") == mood]
    total = len(briefings)
    return {"briefings": briefings[offset: offset + max(1, limit)], "total": total, "offset": offset, "limit": limit}


@router.post("/personal/briefings")
async def create_briefing(request: BriefingCreateRequest) -> dict[str, Any]:
    briefing_id = uuid.uuid4().hex
    briefing = {
        "id": briefing_id,
        "title": request.title or "Briefing",
        "content_text": request.content_text,
        "content_audio_url": request.content_audio_url,
        "generated_at": _now_ms(),
        "mood": request.mood or "neutral",
        "tags": request.tags,
        "meta": request.meta or {},
    }
    _BRIEFINGS[briefing_id] = briefing
    return briefing


@router.get("/personal/briefings/{briefing_id}")
async def get_briefing(briefing_id: str) -> dict[str, Any]:
    briefing = _BRIEFINGS.get(briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="briefing not found")
    return briefing


@router.get("/personal/briefings/latest")
async def get_latest_briefing() -> dict[str, Any]:
    if not _BRIEFINGS:
      raise HTTPException(status_code=404, detail="briefing not found")
    latest = max(_BRIEFINGS.values(), key=lambda item: item.get("generated_at", 0))
    return latest


@router.put("/personal/briefings/{briefing_id}")
async def update_briefing(briefing_id: str, request: BriefingUpdateRequest) -> dict[str, Any]:
    briefing = _BRIEFINGS.get(briefing_id)
    if not briefing:
        raise HTTPException(status_code=404, detail="briefing not found")
    updated = briefing.copy()
    for field, value in request.model_dump(exclude_unset=True).items():
        updated[field] = value
    _BRIEFINGS[briefing_id] = updated
    return updated


@router.delete("/personal/briefings/{briefing_id}")
async def delete_briefing(briefing_id: str) -> dict[str, Any]:
    if briefing_id not in _BRIEFINGS:
        raise HTTPException(status_code=404, detail="briefing not found")
    del _BRIEFINGS[briefing_id]
    return {"status": "ok", "deleted": briefing_id}


@router.post("/api/personal/chat")
async def personal_chat(payload: dict[str, Any]) -> dict[str, Any]:
    message = str(payload.get("message") or payload.get("text") or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    return {
        "source": "local",
        "response": f"I received: {message}",
    }