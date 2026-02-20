from typing import List, Dict
from fastapi import WebSocket

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
