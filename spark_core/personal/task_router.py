"""
Task Management Router — Personal AI task CRUD with persistence.

Endpoints:
  GET    /tasks           — List all tasks (with filters)
  POST   /tasks           — Create new task
  GET    /tasks/{id}      — Get specific task
  PUT    /tasks/{id}      — Update task (partial)
  DELETE /tasks/{id}      — Delete task
  POST   /tasks/{id}/complete — Mark task complete
  GET    /tasks/history   — Get completed task history
  GET    /status          — Health check
"""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
import time

from contracts.models import (
    CreateTaskRequest, UpdateTaskRequest, TaskResponse,
    TaskListResponse, TaskHistoryResponse
)
from . import task_memory
from ..ws.manager import ws_manager

router = APIRouter(tags=["Task"])


@router.get("/status")
async def get_status():
    """Health check endpoint."""
    return {"status": "ok", "module": "Task"}


@router.get("/tasks", response_model=TaskListResponse)
async def list_tasks(
    status: Optional[str] = Query(None),
    priority: Optional[int] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all tasks with optional filtering."""
    try:
        tasks, total = await task_memory.list_tasks(
            status=status,
            priority=priority,
            limit=limit,
            offset=offset,
        )
        return TaskListResponse(tasks=tasks, total=total, offset=offset, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.post("/tasks", response_model=TaskResponse, status_code=201)
async def create_task(req: CreateTaskRequest):
    """Create a new task."""
    try:
        task = await task_memory.create_task(
            title=req.title,
            description=req.description or "",
            status=req.status or "PENDING",
            priority=req.priority or 1,
            due_date=req.due_date,
            tags=req.tags or [],
            recurring=req.recurring,
            meta=req.meta or {},
        )

        # Broadcast to WebSocket clients (non-blocking)
        try:
            await ws_manager.broadcast_json({
                "v": 1,
                "type": "TASK_UPDATE",
                "operation": "created",
                "task_id": task["id"],
                "task": task,
                "ts": time.time() * 1000,
            }, namespace="system")
        except Exception as broadcast_err:
            print(f"Warning: Failed to broadcast task update: {broadcast_err}")

        return TaskResponse(**task)
    except Exception as e:
        import traceback
        print(f"[ERROR] Task creation failed:")
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str):
    """Get a specific task by ID."""
    try:
        task = await task_memory.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        return TaskResponse(**task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")


@router.put("/tasks/{task_id}", response_model=TaskResponse)
async def update_task(task_id: str, req: UpdateTaskRequest):
    """Update a task (partial update)."""
    try:
        # Verify task exists
        existing = await task_memory.get_task(task_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")

        # Prepare update fields (exclude None values)
        update_fields = {}
        for key, value in req.dict().items():
            if value is not None:
                update_fields[key] = value

        task = await task_memory.update_task(task_id, **update_fields)

        # Broadcast to WebSocket clients (non-blocking)
        try:
            await ws_manager.broadcast_json({
                "v": 1,
                "type": "TASK_UPDATE",
                "operation": "updated",
                "task_id": task["id"],
                "task": task,
                "ts": time.time() * 1000,
            }, namespace="system")
        except Exception as broadcast_err:
            print(f"Warning: Failed to broadcast task update: {broadcast_err}")

        return TaskResponse(**task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")


@router.delete("/tasks/{task_id}", status_code=204)
async def delete_task(task_id: str):
    """Delete a task by ID."""
    try:
        # Verify task exists
        existing = await task_memory.get_task(task_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")

        success = await task_memory.delete_task(task_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete task")

        # Broadcast to WebSocket clients (non-blocking)
        try:
            await ws_manager.broadcast_json({
                "v": 1,
                "type": "TASK_UPDATE",
                "operation": "deleted",
                "task_id": task_id,
                "ts": time.time() * 1000,
            }, namespace="system")
        except Exception as broadcast_err:
            print(f"Warning: Failed to broadcast task deletion: {broadcast_err}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete task: {str(e)}")


@router.post("/tasks/{task_id}/complete", response_model=TaskResponse)
async def complete_task(task_id: str):
    """Mark a task as completed."""
    try:
        # Verify task exists
        existing = await task_memory.get_task(task_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Task not found")

        task = await task_memory.complete_task(task_id)

        # Broadcast to WebSocket clients (non-blocking)
        try:
            await ws_manager.broadcast_json({
                "v": 1,
                "type": "TASK_UPDATE",
                "operation": "completed",
                "task_id": task["id"],
                "task": task,
                "ts": time.time() * 1000,
            }, namespace="system")
        except Exception as broadcast_err:
            print(f"Warning: Failed to broadcast task completion: {broadcast_err}")

        return TaskResponse(**task)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to complete task: {str(e)}")


@router.get("/tasks/history", response_model=TaskHistoryResponse)
async def list_task_history(
    task_id: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get task completion history."""
    try:
        history, total = await task_memory.get_task_history(
            task_id=task_id,
            limit=limit,
            offset=offset,
        )
        return TaskHistoryResponse(history=history, total=total, offset=offset, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get history: {str(e)}")
