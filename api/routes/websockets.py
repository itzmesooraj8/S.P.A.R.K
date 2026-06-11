"""S.P.A.R.K. API WebSocket Connection Routers with Token Authentication."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

import GPUtil
import psutil
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

from api.auth import (
    get_operator_username,
    static_operator_token_matches,
    validate_access_token,
)
from security.session_authorization import active_user_var
from tools.sysmon import get_raw_metrics

logger = logging.getLogger("SPARK_WEBSOCKETS")

router = APIRouter(tags=["websockets"])


class ConnectionManager:
    """Manages active WebSocket connections for broad system event broadcasts."""

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
    """Dispatches real-time structured frames directly to connected AI stream consumers."""

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


class VitalsWebSocketRouter:
    """Gathers and streams system metrics (CPU, RAM, GPU, Disk, Battery) at 60 FPS."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._metrics = {}
        self._lock = threading.Lock()
        self._thread = None
        self._running = False

    def start_daemon(self):
        if self._thread is None:
            self._running = True
            self._thread = threading.Thread(
                target=self._update_loop, daemon=True, name="vitals-daemon"
            )
            self._thread.start()

    def stop_daemon(self):
        self._running = False

    def _update_loop(self):
        # Warm up CPU percent
        psutil.cpu_percent(interval=None)
        while self._running:
            try:
                cpu = psutil.cpu_percent(interval=None)
                mem = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                battery = psutil.sensors_battery()

                metrics = {
                    "cpu": cpu,
                    "ramFree": mem.available / (1024**3),
                    "ramTotal": mem.total / (1024**3),
                    "diskFree": disk.free / (1024**3),
                    "diskTotal": disk.total / (1024**3),
                    "batteryPercent": battery.percent if battery else 100,
                    "cpu_percent": cpu,
                    "ram_percent": mem.percent,
                    "ram_used_gb": (mem.total - mem.available) / (1024**3),
                    "ram_total_gb": mem.total / (1024**3),
                    "disk_percent": disk.percent,
                    "gpu_name": "N/A",
                    "gpu_util": 0,
                    "vram_used_mb": 0,
                }
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu = gpus[0]
                        metrics["gpu_name"] = gpu.name
                        metrics["gpu_util"] = gpu.load * 100
                        metrics["vram_used_mb"] = gpu.memoryUsed
                except Exception:
                    pass
                with self._lock:
                    self._metrics = metrics
            except Exception as e:
                logger.error(f"Error in vitals daemon update loop: {e}")
            time.sleep(0.1)

    def get_metrics(self) -> dict:
        with self._lock:
            return dict(self._metrics)

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def stream(self, websocket: WebSocket):
        await self.connect(websocket)
        try:
            # Send initial packet immediately
            initial_metrics = self.get_metrics() or get_raw_metrics()
            await websocket.send_json({"type": "sys_metrics", "payload": initial_metrics})
            while True:
                await asyncio.sleep(0.0166)  # ~60 FPS
                metrics = self.get_metrics()
                if metrics:
                    await websocket.send_json({"type": "sys_metrics", "payload": metrics})
        except WebSocketDisconnect:
            self.disconnect(websocket)
        except Exception as e:
            logger.error(f"Vitals stream connection error: {e}")
            self.disconnect(websocket)


# Global WebSocket instances
manager = ConnectionManager()
ai_manager = AIDispatcher()
vitals_router = VitalsWebSocketRouter()


async def _authenticate_websocket(websocket: WebSocket) -> dict[str, Any] | None:
    """Authenticates WebSocket connection using access token from query params or protocols."""
    token = websocket.query_params.get("token")
    if not token:
        # Check subprotocol or header fallback
        token = websocket.headers.get("x-spark-token") or websocket.headers.get("sec-websocket-protocol")

    if not token:
        return None

    # Validate signed token
    payload = validate_access_token(token)
    if payload:
        return {
            "username": payload.subject,
            "role": payload.role,
            "permissions": list(payload.permissions),
        }

    # Validate static developer token fallback
    if static_operator_token_matches(token):
        from api.auth import _get_operator_permissions, _get_operator_role

        return {
            "username": get_operator_username(),
            "role": _get_operator_role(),
            "permissions": _get_operator_permissions(),
        }

    return None


@router.websocket("/ws")
@router.websocket("/ws/system")
@router.websocket("/ws/vitals")
async def websocket_endpoint(websocket: WebSocket):
    """Streams live machine metrics to client terminals (requires valid bearer auth)."""
    user = await _authenticate_websocket(websocket)
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")
    await vitals_router.stream(websocket)


@router.websocket("/ws/globe")
async def websocket_globe_endpoint(websocket: WebSocket):
    """Simple ping/pong WebSocket channel for map intelligence HUD components."""
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            if message.lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Globe WebSocket error: {e}", exc_info=True)


@router.websocket("/ws/combat")
async def websocket_combat_endpoint(websocket: WebSocket):
    """Simple ping/pong WebSocket channel for defensive system layout HUD."""
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            if message.lower() == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Combat WebSocket error: {e}", exc_info=True)


@router.websocket("/ws/ai")
async def websocket_ai_endpoint(websocket: WebSocket):
    """Interactive streaming WebSocket for real-time agent turn execution and outputs."""
    user = await _authenticate_websocket(websocket)
    if not user:
        raise HTTPException(status_code=401, detail="unauthorized")

    # Set contextvar so it propagates down into the executor thread running _call_tool
    active_user_var.set(user)

    await ai_manager.connect(websocket)
    current_cancel = threading.Event()
    latest_tool_name: str | None = None
    latest_tool_result: Any = None

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
                    import core.main as spark_main

                    if getattr(spark_main, "voice", None):
                        spark_main.voice.stop()
                except Exception as e:
                    logger.error(f"WebSocket cancel error: {e}", exc_info=True)
                await websocket.send_json(
                    {"type": "ERROR", "message": "Generation cancelled.", "code": "cancelled"}
                )
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
                nonlocal latest_tool_name, latest_tool_result
                normalized_type = (
                    event_type
                    if event_type in {"response_token", "response_done", "status", "error"}
                    else event_type.upper()
                )
                frame: dict[str, Any] = {"type": normalized_type, **payload}
                if normalized_type == "tool_result":
                    latest_tool_name = str(payload.get("tool") or "")
                    latest_tool_result = payload.get("output")
                if normalized_type in {"response_done", "error"}:
                    done_emitted.set()
                loop.call_soon_threadsafe(queue.put_nowait, frame)

            forward_task = asyncio.create_task(_forward(queue))
            await websocket.send_json({"type": "STATUS", "state": "thinking"})

            try:
                from core.main import run_agent_turn

                # Carry the current active context into the worker thread
                ctx = contextvars.copy_context()
                result = await asyncio.to_thread(
                    ctx.run, run_agent_turn, text, True, False, sink, current_cancel
                )
                if latest_tool_name in {"get_news", "get_weather"} and latest_tool_result is not None:
                    await websocket.send_json(
                        {
                            "type": "widget",
                            "widget": latest_tool_name.replace("get_", ""),
                            "data": latest_tool_result,
                        }
                    )
                if not done_emitted.is_set():
                    await queue.put({"type": "response_done", "content": result})
            finally:
                await queue.put({"type": "__close__"})
                await forward_task

    except WebSocketDisconnect:
        ai_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"AI WebSocket error: {e}", exc_info=True)
        ai_manager.disconnect(websocket)
    finally:
        ai_manager.disconnect(websocket)


@router.websocket("/ws/personal/chat")
async def websocket_personal_chat(websocket: WebSocket):
    """Echo personal chat interface WebSocket."""
    await websocket.accept()
    try:
        while True:
            message = await websocket.receive_text()
            if not message.strip():
                continue
            await websocket.send_text(f"SPARK Personal AI: {message}")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Personal Chat WebSocket error: {e}", exc_info=True)
