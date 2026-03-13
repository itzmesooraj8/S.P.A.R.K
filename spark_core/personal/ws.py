import asyncio
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Any

from .brain import personal_brain

# WebSocket route for PersonaPlex-style full-duplex communication
router = APIRouter(prefix="/ws/personal", tags=["personal_ai_ws"])

class PersonalWSManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                pass

personal_ws_manager = PersonalWSManager()

@router.websocket("/chat")
async def websocket_endpoint(websocket: WebSocket):
    """
    Full-duplex WebSocket endpoint for PersonaPlex voice and fast-chat capabilities.
    Listens and responds simultaneously.
    """
    await personal_ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # PersonaPlex handles streams, for now we will send chunks back
            reply = personal_brain.route(data)
            await personal_ws_manager.send_personal_message(reply, websocket)
    except WebSocketDisconnect:
        personal_ws_manager.disconnect(websocket)
        print("Personal assistant disconnected")

