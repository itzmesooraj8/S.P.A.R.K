import asyncio
import json
from typing import List, Dict, Any
from fastapi import WebSocket
from system.state import unified_state
from intelligence.registry import project_registry

# Max outbound messages buffered per session before backpressure drops oldest.
_SESSION_QUEUE_MAXSIZE = 1024
# Only log WS drop warnings once every N drops to avoid terminal flood.
_DROP_LOG_INTERVAL = 50

class WebSocketManager:
    def __init__(self):
        # Store connections by namespace
        # keys: "ai", "system", "device", "notifications", "admin", "combat"
        self.active_connections: Dict[str, List[WebSocket]] = {
            "ai": [],
            "system": [],
            "device": [],
            "notifications": [],
            "admin": [],
            "combat": [],
        }
        # session_id → websocket for targeted routing
        self.session_connections: Dict[str, WebSocket] = {}
        # Per-session bounded async send queue (backpressure protection)
        self._session_queues: Dict[str, asyncio.Queue] = {}
        # Per-session background sender tasks
        self._session_sender_tasks: Dict[str, asyncio.Task] = {}
        # Per-session dropped message counters (for observability)
        self._session_dropped: Dict[str, int] = {}

        unified_state.subscribe_async(self._on_state_change)

    async def _on_state_change(self, state: Dict[str, Any], version: int, timestamp: float):
        # Prevent MemoryError by stripping out the massive raw graph nodes/edges
        state_copy = state.copy()
        if "code_graph" in state_copy:
            cg = state_copy["code_graph"]
            state_copy["code_graph"] = {
                "nodes_count": len(cg.get("nodes", [])),
                "edges_count": len(cg.get("edges", [])),
                "summary_only": True
            }

        payload = {
            "type": "STATE_UPDATE",
            "version": version,
            "timestamp": timestamp,
            "project_id": getattr(project_registry, 'current_focus', 'global'),
            "state": state_copy
        }
        await self.broadcast(json.dumps(payload), "system")

    async def connect(self, websocket: WebSocket, namespace: str):
        await websocket.accept()
        if namespace in self.active_connections:
            self.active_connections[namespace].append(websocket)
            print(f"📡 [WS] Connection added to '{namespace}'. Total: {len(self.active_connections[namespace])}")

    def register_session(self, session_id: str, websocket: WebSocket):
        """Map a session_id to its websocket and start a background sender queue."""
        self.session_connections[session_id] = websocket

        # Create a bounded queue and a long-lived sender coroutine for this session.
        queue: asyncio.Queue = asyncio.Queue(maxsize=_SESSION_QUEUE_MAXSIZE)
        self._session_queues[session_id] = queue
        sender_task = asyncio.create_task(
            self._session_sender(session_id, websocket, queue),
            name=f"ws_sender_{session_id[:8]}"
        )
        self._session_sender_tasks[session_id] = sender_task
        self._session_dropped[session_id] = 0
        print(f"📡 [WS] Session registered + sender started: {session_id[:8]}...")

    async def _session_sender(self, session_id: str, websocket: WebSocket, queue: asyncio.Queue):
        """Drain the per-session queue and send each item. Stops on sentinel (None) or error."""
        try:
            while True:
                item = await queue.get()
                if item is None:  # Sentinel: session is being torn down
                    break
                try:
                    await websocket.send_json(item)
                except Exception as e:
                    print(f"⚠️ [WS] Session sender error for {session_id[:8]}: {e}")
                    break
        finally:
            print(f"📡 [WS] Session sender stopped: {session_id[:8]}...")

    def disconnect(self, websocket: WebSocket, namespace: str):
        if namespace in self.active_connections:
            if websocket in self.active_connections[namespace]:
                self.active_connections[namespace].remove(websocket)
                print(f"📡 [WS] Disconnected from '{namespace}'.")

        # Clean up session mapping + signal sender shutdown
        dead = [sid for sid, ws in self.session_connections.items() if ws is websocket]
        for sid in dead:
            del self.session_connections[sid]
            # Signal the sender coroutine to stop gracefully
            q = self._session_queues.pop(sid, None)
            if q:
                try:
                    q.put_nowait(None)  # sentinel
                except asyncio.QueueFull:
                    pass
            task = self._session_sender_tasks.pop(sid, None)
            if task and not task.done():
                task.cancel()
            self._session_dropped.pop(sid, None)
            print(f"📡 [WS] Session removed: {sid[:8]}...")

    async def send_to_session(self, session_id: str, data: dict):
        """Enqueue a JSON payload for a specific session (non-blocking, bounded backpressure)."""
        queue = self._session_queues.get(session_id)
        if queue is None:
            return
        if queue.full():
            # Drop oldest item to make room (maintain freshness, not completeness)
            try:
                queue.get_nowait()
                dropped = self._session_dropped.get(session_id, 0) + 1
                self._session_dropped[session_id] = dropped
                # Only log every _DROP_LOG_INTERVAL drops to prevent terminal flood
                if dropped % _DROP_LOG_INTERVAL == 1:
                    print(f"⚠️ [WS] Session queue pressure for {session_id[:8]}; drop #{dropped} (logged every {_DROP_LOG_INTERVAL}).")
            except asyncio.QueueEmpty:
                pass
        try:
            queue.put_nowait(data)
        except asyncio.QueueFull:
            pass  # Extremely unlikely after the drop above; silently discard

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, namespace: str):
        if namespace in self.active_connections:
            for connection in list(self.active_connections[namespace]):
                try:
                    await connection.send_text(message)
                except Exception as e:
                    print(f"⚠️ [WS] Broadcast error in '{namespace}': {e}")
                    self.disconnect(connection, namespace)

    async def broadcast_json(self, data: dict, namespace: str):
        if namespace in self.active_connections:
            for connection in list(self.active_connections[namespace]):
                try:
                    await connection.send_json(data)
                except Exception as e:
                    print(f"⚠️ [WS] Broadcast_json error in '{namespace}': {e}")
                    self.disconnect(connection, namespace)

    async def send_json(self, data: dict, websocket: WebSocket):
        try:
            await websocket.send_json(data)
        except Exception as e:
            print(f"⚠️ [WS] send_json error: {e}")

    def get_runtime_stats(self) -> dict:
        """Return live runtime counters for the /api/health/runtime endpoint."""
        sessions = {}
        for sid, q in self._session_queues.items():
            task = self._session_sender_tasks.get(sid)
            sessions[f"session_{sid[:8]}"] = {
                "queue_size": q.qsize(),
                "queue_capacity": _SESSION_QUEUE_MAXSIZE,
                "dropped_messages": self._session_dropped.get(sid, 0),
                "sender_alive": task is not None and not task.done(),
            }
        return {
            "active_sessions": len(self.session_connections),
            "namespace_connections": {
                ns: len(conns) for ns, conns in self.active_connections.items()
            },
            "sessions": sessions,
        }

ws_manager = WebSocketManager()

