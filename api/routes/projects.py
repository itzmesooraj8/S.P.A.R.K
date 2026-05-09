from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter()

_ACTIVE_PROJECTS = ["SPARK Core", "HUD Frontend", "Memory Graph", "Combat Ops"]
_CURRENT_FOCUS = _ACTIVE_PROJECTS[0]


class FocusSwitchRequest(BaseModel):
    project_id: str = Field(min_length=1)


@router.get("/api/projects")
async def list_projects() -> dict[str, Any]:
    return {
        "active_projects": _ACTIVE_PROJECTS,
        "current_focus": _CURRENT_FOCUS,
    }


@router.post("/api/projects/switch/{project_id}")
async def switch_project(project_id: str) -> dict[str, Any]:
    global _CURRENT_FOCUS
    if not project_id.strip():
        raise HTTPException(status_code=400, detail="project_id required")
    _CURRENT_FOCUS = project_id
    return {
        "status": "ok",
        "current_focus": _CURRENT_FOCUS,
    }


@router.get("/api/projects/analyze")
async def analyze_projects() -> dict[str, Any]:
    return {
        "status": "ok",
        "current_focus": _CURRENT_FOCUS,
        "summary": "Project analysis is available in compatibility mode.",
        "recommendations": [
            {"id": "focus", "type": "focus", "severity": "medium", "confidence": 0.72, "title": "Keep the HUD centered on runtime state."},
            {"id": "reduce-noise", "type": "ui", "severity": "high", "confidence": 0.81, "title": "Hide developer telemetry by default."},
        ],
    }


@router.get("/api/projects/optimize/{project_id}")
async def optimize_project(project_id: str) -> dict[str, Any]:
    return {
        "status": "ok",
        "project_id": project_id,
        "recommendations": [
            {"id": "r1", "type": "layout", "severity": "medium", "confidence": 0.77, "title": "Compress the left and right rails into focused summaries."},
            {"id": "r2", "type": "motion", "severity": "high", "confidence": 0.84, "title": "Tie ribbon states to live runtime phase transitions."},
        ],
    }


@router.post("/api/projects/optimize/feedback")
async def optimize_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    return {"status": "ok", "received": payload}