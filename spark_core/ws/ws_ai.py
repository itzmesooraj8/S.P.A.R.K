import json
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from auth.jwt_handler import require_ws_auth
from system.event_bus import event_bus
from ws.manager import ws_manager

ws_ai_router = APIRouter()


def _resolve_memory_session_id(websocket: WebSocket, auth_payload: dict) -> str:
    requested = str(websocket.query_params.get("conversation_id", "")).strip()
    if requested:
        return requested[:128]

    subject = str((auth_payload or {}).get("sub", "")).strip()
    if subject:
        return f"user:{subject}"[:128]

    return "default"


def _parse_frame(raw_data: str):
    """
    Accepts both legacy raw-text frames and JSON envelopes.
    Returns (kind, payload) where kind is one of: USER_INPUT, CANCEL, IGNORE.
    """
    text = (raw_data or "").strip()
    if not text:
        return "IGNORE", {}

    try:
        frame = json.loads(text)
    except json.JSONDecodeError:
        return "USER_INPUT", {"content": text}

    if isinstance(frame, str):
        frame_text = frame.strip()
        return ("USER_INPUT", {"content": frame_text}) if frame_text else ("IGNORE", {})

    if not isinstance(frame, dict):
        return "IGNORE", {}

    frame_type = str(frame.get("type", "")).upper()
    if frame_type == "CANCEL":
        return "CANCEL", {}

    if frame_type == "USER_INPUT":
        content = str(frame.get("content", "")).strip()
        return ("USER_INPUT", {"content": content}) if content else ("IGNORE", {})

    content = str(frame.get("message") or frame.get("content") or "").strip()
    if content:
        return "USER_INPUT", {"content": content}

    return "IGNORE", {}

@ws_ai_router.websocket("/ws/ai")
async def ai_websocket_handler(websocket: WebSocket):
    auth_payload = await require_ws_auth(websocket, min_role="OPERATOR")
    if auth_payload is None:
        return
    websocket.state.auth = auth_payload
    memory_session_id = _resolve_memory_session_id(websocket, auth_payload)

    await ws_manager.connect(websocket, "ai")
    session_id = str(uuid.uuid4())
    ws_manager.register_session(session_id, websocket)

    await websocket.send_json({
        "type": "status",
        "status": "connected",
        "session_id": session_id,
        "memory_session_id": memory_session_id,
    })

    try:
        while True:
            raw_data = await websocket.receive_text()
            kind, payload = _parse_frame(raw_data)

            if kind == "CANCEL":
                event_bus.publish("cancel_task", {"session_id": session_id})
                continue

            if kind == "USER_INPUT":
                event_bus.publish("user_input", {
                    "data": payload["content"],
                    "session_id": session_id,
                    "memory_session_id": memory_session_id,
                })

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "ai")
    except Exception:
        ws_manager.disconnect(websocket, "ai")
