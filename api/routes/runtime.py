from __future__ import annotations

from fastapi import APIRouter

from core.camera_vision import analyze_camera_frame, capture_camera_frame
from core.runtime_architecture import build_runtime_architecture
from core.orchestrator.runtime_state import get_runtime_snapshot
from tools.iot import control_smart_plug


router = APIRouter()


@router.get("/api/runtime/architecture")
async def runtime_architecture():
    return build_runtime_architecture()


@router.get("/api/runtime/orchestrator")
async def runtime_orchestrator():
    return get_runtime_snapshot()


@router.get("/api/runtime/dashboard")
async def runtime_dashboard():
    snapshot = get_runtime_snapshot()
    last_intent = snapshot.get("last_intent") or {}
    last_route = snapshot.get("last_route") or {}
    graph = last_route.get("graph") if isinstance(last_route, dict) else {}
    nodes = graph.get("nodes") if isinstance(graph, dict) else []

    return {
        "active_intent": last_intent.get("summary") or last_intent.get("name") or snapshot.get("mode", "idle"),
        "selected_agent": snapshot.get("last_agent") or "system_agent",
        "inference_mode": snapshot.get("inference_source") or "local",
        "task_graph": {
            "nodes": len(nodes) if isinstance(nodes, list) else 0,
            "active_node": (
                nodes[0].get("action")
                if isinstance(nodes, list) and nodes and isinstance(nodes[0], dict)
                else None
            ),
        },
        "queue_depth": snapshot.get("queue_depth", 0),
        "runtime_state": snapshot.get("mode", "idle"),
        "memory_hits": snapshot.get("memory_hits", 0),
        "retrievals": snapshot.get("retrievals", 0),
        "events": [event.get("type") for event in snapshot.get("last_events", []) if isinstance(event, dict)],
        "snapshot": snapshot,
        "architecture": build_runtime_architecture(),
    }


@router.get("/api/runtime/camera/scan")
async def runtime_camera_scan():
    frame_path = capture_camera_frame()
    if frame_path.endswith(".jpg"):
        return {"frame": frame_path, "analysis": analyze_camera_frame(frame_path)}
    return {"frame": frame_path, "analysis": frame_path}


@router.post("/api/runtime/smart-home/plug/{action}")
async def runtime_smart_plug(action: str):
    return {"result": control_smart_plug(action)}

