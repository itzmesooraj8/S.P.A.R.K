from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import sys
import os
import uuid

# Add parent directory to path to import tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.sysmon import get_raw_metrics
from api.routes.memory import router as memory_router
from api.routes.task import router as task_router

app = FastAPI(title="S.P.A.R.K. Bridge API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(memory_router)
app.include_router(task_router)


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
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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

@app.post("/internal/broadcast")
async def broadcast_event(request: Request):
    """Webhook for core/main.py to send events (voice, log, portfolio) to HUD"""
    data = await request.json()
    await manager.broadcast(data)
    return {"status": "ok"}
