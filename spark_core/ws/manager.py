import json
from typing import List, Dict, Any
from fastapi import WebSocket
from system.state import unified_state
from intelligence.registry import project_registry

class WebSocketManager:
    def __init__(self):
        # Store connections by namespace
        # keys: "ai", "system", "device", "notifications", "admin"
        self.active_connections: Dict[str, List[WebSocket]] = {
            "ai": [],
            "system": [],
            "device": [],
            "notifications": [],
            "admin": []
        }
        # Subscription binds to project_registry active context in switch_focus
        # Leaving the legacy unified_state bound as a fallback if no project is active, OR we can deprecate it entirely.
        # But for smooth transition, we'll keep `unified_state` bound as a global fallover, and let the broadcast tag it.
        unified_state.subscribe_async(self._on_state_change)

    async def _on_state_change(self, state: Dict[str, Any], version: int, timestamp: float):
        payload = {
            "type": "STATE_UPDATE",
            "version": version,
            "timestamp": timestamp,
            "project_id": getattr(project_registry, 'current_focus', 'global'),
            "state": state
        }
        await self.broadcast(json.dumps(payload), "system")

    async def connect(self, websocket: WebSocket, namespace: str):
        await websocket.accept()
        if namespace in self.active_connections:
            self.active_connections[namespace].append(websocket)
            print(f"📡 [WS] Connection added to '{namespace}'. Total: {len(self.active_connections[namespace])}")

    def disconnect(self, websocket: WebSocket, namespace: str):
        if namespace in self.active_connections:
            if websocket in self.active_connections[namespace]:
                self.active_connections[namespace].remove(websocket)
                print(f"📡 [WS] Disconnected from '{namespace}'.")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, namespace: str):
        if namespace in self.active_connections:
            # We must iterate over a copy in case of disconnections
            for connection in list(self.active_connections[namespace]):
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"⚠️ [WS] Broadcast error in '{namespace}': {e}")
                    self.disconnect(connection, namespace)

ws_manager = WebSocketManager()
