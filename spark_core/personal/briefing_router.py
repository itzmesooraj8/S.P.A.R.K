"""
Briefing Management Router — Personal AI morning briefing CRUD with persistence.

Endpoints:
  GET    /briefings           — List all briefings (with filters)
  POST   /briefings           — Create new briefing
  GET    /briefings/latest    — Get latest briefing
  GET    /briefings/{id}      — Get specific briefing
  PUT    /briefings/{id}      — Update briefing (partial)
  DELETE /briefings/{id}      — Delete briefing
  GET    /status              — Health check
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
import time

from contracts.models import (
    CreateBriefingRequest, UpdateBriefingRequest, BriefingResponse,
    BriefingListResponse
)
from . import briefing_memory
from ..ws.manager import ws_manager

router = APIRouter(tags=["Briefing"])


@router.get("/status")
async def get_status():
    """Health check endpoint."""
    return {"status": "ok", "module": "Briefing"}


@router.get("/briefings", response_model=BriefingListResponse)
async def list_briefings(
    mood: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """List all briefings with optional filtering."""
    try:
        briefings, total = await briefing_memory.list_briefings(
            mood=mood,
            limit=limit,
            offset=offset,
        )
        return BriefingListResponse(briefings=briefings, total=total, offset=offset, limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list briefings: {str(e)}")


@router.post("/briefings", response_model=BriefingResponse, status_code=201)
async def create_briefing(req: CreateBriefingRequest):
    """Create a new briefing."""
    try:
        briefing = await briefing_memory.create_briefing(
            content_text=req.content_text,
            title=req.title or "Morning Briefing",
            content_audio_url=req.content_audio_url,
            mood=req.mood or "NEUTRAL",
            tags=req.tags or [],
            meta=req.meta or {},
        )

        # Broadcast to WebSocket clients (non-blocking)
        try:
            await ws_manager.broadcast_json({
                "v": 1,
                "type": "BRIEFING_UPDATE",
                "operation": "created",
                "briefing_id": briefing["id"],
                "briefing": briefing,
                "ts": time.time() * 1000,
            }, namespace="system")
        except Exception as broadcast_err:
            print(f"Warning: Failed to broadcast briefing update: {broadcast_err}")

        return BriefingResponse(**briefing)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create briefing: {str(e)}")


@router.get("/briefings/latest", response_model=BriefingResponse)
async def get_latest_briefing():
    """Get the most recently generated briefing."""
    try:
        briefing = await briefing_memory.get_latest_briefing()
        if not briefing:
            raise HTTPException(status_code=404, detail="No briefings found")
        return BriefingResponse(**briefing)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get latest briefing: {str(e)}")


@router.get("/briefings/{briefing_id}", response_model=BriefingResponse)
async def get_briefing(briefing_id: str):
    """Get a specific briefing by ID."""
    try:
        briefing = await briefing_memory.get_briefing(briefing_id)
        if not briefing:
            raise HTTPException(status_code=404, detail="Briefing not found")
        return BriefingResponse(**briefing)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get briefing: {str(e)}")


@router.put("/briefings/{briefing_id}", response_model=BriefingResponse)
async def update_briefing(briefing_id: str, req: UpdateBriefingRequest):
    """Update a briefing (partial update)."""
    try:
        # Verify briefing exists
        existing = await briefing_memory.get_briefing(briefing_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Briefing not found")

        # Prepare update fields (exclude None values)
        update_fields = {}
        for key, value in req.dict().items():
            if value is not None:
                update_fields[key] = value

        briefing = await briefing_memory.update_briefing(briefing_id, **update_fields)

        # Broadcast to WebSocket clients (non-blocking)
        try:
            await ws_manager.broadcast_json({
                "v": 1,
                "type": "BRIEFING_UPDATE",
                "operation": "updated",
                "briefing_id": briefing["id"],
                "briefing": briefing,
                "ts": time.time() * 1000,
            }, namespace="system")
        except Exception as broadcast_err:
            print(f"Warning: Failed to broadcast briefing update: {broadcast_err}")

        return BriefingResponse(**briefing)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update briefing: {str(e)}")


@router.delete("/briefings/{briefing_id}", status_code=204)
async def delete_briefing(briefing_id: str):
    """Delete a briefing by ID."""
    try:
        # Verify briefing exists
        existing = await briefing_memory.get_briefing(briefing_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Briefing not found")

        success = await briefing_memory.delete_briefing(briefing_id)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete briefing")

        # Broadcast to WebSocket clients (non-blocking)
        try:
            await ws_manager.broadcast_json({
                "v": 1,
                "type": "BRIEFING_UPDATE",
                "operation": "deleted",
                "briefing_id": briefing_id,
                "ts": time.time() * 1000,
            }, namespace="system")
        except Exception as broadcast_err:
            print(f"Warning: Failed to broadcast briefing deletion: {broadcast_err}")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete briefing: {str(e)}")
