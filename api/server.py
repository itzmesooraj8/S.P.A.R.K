from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import sys
import os
import uuid
import json
import threading
from typing import Any

# Add parent directory to path to import tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.sysmon import get_raw_metrics
from api.routes.memory import router as memory_router
from api.routes.projects import router as projects_router
from api.routes.personal import router as personal_router
from api.routes.task import router as task_router
from api.routes.runtime import router as runtime_router
from api.routes.security import router as security_router
import core.main as spark_main
from core.main import run_agent_turn

import logging

logger = logging.getLogger(__name__)

app = FastAPI(title="S.P.A.R.K. Bridge API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(memory_router)
app.include_router(projects_router)
app.include_router(personal_router)
app.include_router(task_router)
app.include_router(runtime_router)
app.include_router(security_router)


@app.post("/api/auth/login")
async def auth_login():
    token = uuid.uuid4().hex
    return {
        "access_token": token,
        "refresh_token": token,
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {"username": "operator", "role": "operator"},
    }


@app.post("/api/auth/refresh")
async def auth_refresh():
    token = uuid.uuid4().hex
    return {
        "access_token": token,
        "refresh_token": token,
        "token_type": "bearer",
        "expires_in": 3600,
        "user": {"username": "operator", "role": "operator"},
    }


@app.post("/api/auth/logout")
async def auth_logout():
    return {"status": "ok"}


@app.get("/health")
async def health_check():
    return {"status": "ok"}

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Failed to broadcast to {connection.client}: {e}")


class AIDispatcher:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send(self, websocket: WebSocket, message: dict[str, Any]):
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Failed to send to {websocket.client}: {e}")

manager = ConnectionManager()
ai_manager = AIDispatcher()

async def _system_websocket(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Push initial sysmon state immediately
        await websocket.send_json({
            "type": "sys_metrics",
            "payload": get_raw_metrics()
        })
        
        # Then loop every 2s
        while True:
            await asyncio.sleep(2)
            await websocket.send_json({
                "type": "sys_metrics",
                "payload": get_raw_metrics()
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)


@app.websocket("/ws")
@app.websocket("/ws/system")
async def websocket_endpoint(websocket: WebSocket):
    await _system_websocket(websocket)


@app.websocket("/ws/globe")
async def websocket_globe_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            if message.lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.websocket("/ws/combat")
async def websocket_combat_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            if message.lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception:
        pass


@app.websocket("/ws/ai")
async def websocket_ai_endpoint(websocket: WebSocket):
    await ai_manager.connect(websocket)
    current_cancel = threading.Event()

    async def _forward(queue: asyncio.Queue[dict[str, Any]]):
        while True:
            message = await queue.get()
            if message.get("type") == "__close__":
                return
            await ai_manager.send(websocket, message)

    try:
        while True:
            data = await websocket.receive_json()
            message_type = str(data.get("type") or data.get("messageType") or "").upper()

            if message_type == "CANCEL":
                current_cancel.set()
                try:
                    if spark_main.voice:
                        spark_main.voice.stop()
                except Exception:
                    pass
                await websocket.send_json({"type": "ERROR", "message": "Generation cancelled.", "code": "cancelled"})
                await websocket.send_json({"type": "DONE"})
                continue

            text = str(data.get("content") or data.get("message") or "").strip()
            if not text:
                continue

            current_cancel = threading.Event()
            queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
            done_emitted = threading.Event()
            loop = asyncio.get_running_loop()

            def sink(event_type: str, payload: dict[str, Any]):
                normalized_type = event_type if event_type in {"response_token", "response_done", "status", "error"} else event_type.upper()
                frame: dict[str, Any] = {"type": normalized_type, **payload}
                if normalized_type in {"response_done", "error"}:
                    done_emitted.set()
                loop.call_soon_threadsafe(queue.put_nowait, frame)

            forward_task = asyncio.create_task(_forward(queue))
            await websocket.send_json({"type": "STATUS", "state": "thinking"})

            try:
                result = await asyncio.to_thread(run_agent_turn, text, True, False, sink, current_cancel)
                if not done_emitted.is_set():
                    await queue.put({"type": "response_done", "content": result})
            finally:
                await queue.put({"type": "__close__"})
                await forward_task

    except WebSocketDisconnect:
        ai_manager.disconnect(websocket)
    except Exception:
        ai_manager.disconnect(websocket)
    finally:
        ai_manager.disconnect(websocket)


@app.websocket("/ws/personal/chat")
async def websocket_personal_chat(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            if not message.strip():
                continue
            await websocket.send_text(f"SPARK Personal AI: {message}")
    except WebSocketDisconnect:
        pass
    except Exception:
        pass

@app.post("/internal/broadcast")
async def broadcast_event(request: Request):
    """Webhook for core/main.py to send events (voice, log, portfolio) to HUD"""
    data = await request.json()
    await manager.broadcast(data)
    return {"status": "ok"}
