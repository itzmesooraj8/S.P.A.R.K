from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi import Depends, Header, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
import time
from collections import defaultdict
from pydantic import BaseModel
import subprocess

logger = logging.getLogger(__name__)
import sys
import os
import uuid
import threading
from typing import Any
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "api", "static")

# Add parent directory to path to import tools
sys.path.append(BASE_DIR)
from tools.sysmon import get_raw_metrics
from tools.voice import listen_and_transcribe, speak, load_whisper
from api.routes.memory import router as memory_router
from api.routes.projects import router as projects_router
from api.routes.personal import router as personal_router
from api.routes.task import router as task_router
from api.routes.runtime import router as runtime_router
from api.routes.security import router as security_router
import core.main as spark_main
from core.main import run_agent_turn
from core.scheduler import init_scheduler
from core.heartbeat import start_heartbeat
from core.takeover import start_takeover_mode
from core.spark_brain import handle as spark_brain_handle
from core.spark_brain import memory as spark_memory
from core.memory import MemoryCategory
from core.wake_word import start_wake_engine

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

SPARK_TOKEN = os.getenv("SPARK_TOKEN", "change-this-token")
request_counts: defaultdict[str, list[float]] = defaultdict(list)


async def verify_token(x_spark_token: str = Header(None)):
    if x_spark_token != SPARK_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")


async def rate_limit(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    request_counts[ip] = [timestamp for timestamp in request_counts[ip] if now - timestamp < 60]
    if len(request_counts[ip]) >= 60:
        raise HTTPException(status_code=429, detail="Rate limit exceeded")
    request_counts[ip].append(now)


@app.on_event("startup")
async def startup_tasks():
    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, load_whisper)
    except Exception as exc:
        logger.warning(f"Whisper preload failed: {exc}")

    try:
        init_scheduler()
    except Exception as exc:
        logger.warning(f"Scheduler startup failed: {exc}")

    try:
        start_heartbeat()
    except Exception as exc:
        logger.warning(f"Heartbeat startup failed: {exc}")

    try:
        start_takeover_mode()
    except Exception as exc:
        logger.warning(f"Takeover startup failed: {exc}")

    _wake_lock = threading.Lock()

    def on_wake():
        if not _wake_lock.acquire(blocking=False):
            return  # already processing, skip
        try:
            resp = requests.post("http://localhost:8000/listen", timeout=30)
            reply = resp.json().get("reply", "")
            print(f"[SPARK] {reply}")
        except Exception as exc:
            print(f"[SPARK] Wake handler error: {exc}")
        finally:
            _wake_lock.release()

    try:
        use_hotword = os.getenv("SPARK_ENABLE_HOTWORD", "1").strip().lower() in {"1", "true", "yes", "on"}
        start_wake_engine(on_wake_callback=on_wake, use_hotword=use_hotword)
    except Exception as exc:
        logger.warning(f"Wake engine startup failed: {exc}")

    # Start Cloudflare tunnel if enabled for remote Signal Override
    enable_tunnel = os.getenv("SPARK_ENABLE_TUNNEL", "0").strip().lower() in {"1", "true", "yes", "on"}
    if enable_tunnel:
        try:
            tunnel_proc = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            time.sleep(2)  # Give tunnel time to start
            logger.info("[SPARK] Cloudflare tunnel starting for remote Signal Override")
        except Exception as exc:
            logger.warning(f"Cloudflare tunnel startup failed: {exc}")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)

# Note: mount should be last to avoid catching API routes
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/", response_class=HTMLResponse)
async def get_index():
    with open(os.path.join(STATIC_DIR, "index.html"), "r", encoding="utf-8") as index_file:
        return HTMLResponse(index_file.read())


@app.get("/override", response_class=HTMLResponse)
async def get_override():
    """Serve the mobile Signal Override UI (no auth required for discovery)."""
    override_path = os.path.join(STATIC_DIR, "override.html")
    if not os.path.exists(override_path):
        return HTMLResponse("<h1>Signal Override not configured</h1>", status_code=404)
    with open(override_path, "r", encoding="utf-8") as override_file:
        return HTMLResponse(override_file.read())


@app.post("/api/override/cast")
async def cast_signal_override(request: Request, x_spark_token: str = Header(None)):
    """Remote Signal Override: cast to any display running SPARK HUD.
    
    Requires X-SPARK-TOKEN header matching SPARK_TOKEN.
    Broadcasts signal_override event to all connected WebSocket clients.
    """
    if x_spark_token != SPARK_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    try:
        body = await request.json()
        target_url = body.get("target_url", "localhost:8000")
        payload = body.get("payload", {})
    except Exception:
        return {"error": "Invalid payload"}, 400
    
    # Broadcast Signal Override event to all connected HUD clients
    await manager.broadcast({
        "type": "signal_override",
        "target_url": target_url,
        "payload": payload,
        "timestamp": time.time(),
    })
    
    return {"status": "signal cast", "clients_notified": len(manager.active_connections)}
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


@app.get("/status", dependencies=[Depends(verify_token), Depends(rate_limit)])
@app.get("/api/status", dependencies=[Depends(verify_token), Depends(rate_limit)])
async def status():
    return {"status": "ok", "service": "S.P.A.R.K"}


@app.get("/memory")
async def get_memory_stats():
    try:
        results = spark_memory.collection.get(where={"category": "fact"})
        facts_count = len(results["ids"]) if results and "ids" in results else 0
    except Exception:
        facts_count = 0

    return {
        "total": spark_memory.count(),
        "facts": facts_count,
        "recent": spark_memory.recall("last conversation", top_k=5),
    }

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    logger.info("chat_endpoint: direct brain path entered")
    # Call the async Groq brain directly for HTTP chat so the endpoint does not
    # depend on the heavier sync voice/runtime wrapper.
    try:
        result = await spark_brain_handle(request.message, [])
        return {"response": str(result.get("reply", "")).strip()}
    except Exception as exc:
        logger.error(f"Chat endpoint failed: {exc}", exc_info=True)
        return {"response": "I’m having trouble reaching the language model right now. Please try again in a moment."}


@app.post("/listen")
async def listen_endpoint():
    """Record 5s of audio, transcribe, run through SPARK."""
    loop = asyncio.get_running_loop()
    text = await loop.run_in_executor(None, listen_and_transcribe, 5)
    if not text:
        return {"error": "No speech detected"}
    result = await spark_brain_handle(text, [])
    await speak(result["reply"])
    result["transcript"] = text
    return result

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
                logger.error(f"WebSocket error: {e}", exc_info=True)


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
            logger.error(f"WebSocket error: {e}", exc_info=True)

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
        logger.error(f"System WebSocket error: {e}", exc_info=True)
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
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


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
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)


@app.websocket("/ws/ai")
async def websocket_ai_endpoint(websocket: WebSocket):
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
                    if spark_main.voice:
                        spark_main.voice.stop()
                except Exception as e:
                    logger.error(f"WebSocket error: {e}", exc_info=True)
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
                nonlocal latest_tool_name, latest_tool_result
                normalized_type = event_type if event_type in {"response_token", "response_done", "status", "error"} else event_type.upper()
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
                result = await asyncio.to_thread(run_agent_turn, text, True, False, sink, current_cancel)
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
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)

@app.post("/internal/broadcast")
async def broadcast_event(request: Request):
    """Webhook for core/main.py to send events (voice, log, portfolio) to HUD"""
    data = await request.json()
    await manager.broadcast(data)
    return {"status": "ok"}
