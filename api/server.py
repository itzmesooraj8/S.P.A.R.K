"""S.P.A.R.K. API Server.

This file serves as the main entry point to register routers, middlewares,
CORS permissions, static folders, and coordinate startup lifecycle tasks.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Any

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

# Configure logging first
logger = logging.getLogger("SPARK_SERVER")


def _configure_logging() -> None:
    if logger.handlers:
        return
    log_path = os.path.join(BASE_DIR, "spark.log")
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )


_configure_logging()

# Imports from modular routers and services
from api.auth import verify_token
from api.biometric_stream import router as biometric_router
from api.routes.auth import router as auth_router
from api.routes.chat import rate_limit, router as chat_router
from api.routes.memory import router as memory_router
from api.routes.override import router as override_router
from api.routes.personal import router as personal_router
from api.routes.projects import router as projects_router
from api.routes.runtime import router as runtime_router
from api.routes.satellite import router as satellite_router
from api.routes.security import router as security_router
from api.routes.task import router as task_router
from api.routes.websockets import manager, router as websockets_router, vitals_router, VitalsWebSocketRouter
from api.startup import execute_shutdown_sequence, execute_startup_sequence, TelemetryRefresher, telemetry_refresher


def broadcast_system_alert(alert_payload: dict[str, Any]) -> None:
    """Legacy compatibility wrapper for broadcasting system alerts to WebSockets."""
    import api.startup as startup
    import asyncio
    msg = {
        "type": "system_alert",
        "payload": alert_payload,
        "timestamp": time.time(),
    }
    try:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        target_loop = running_loop or getattr(startup, "_broadcast_loop", None)
        if target_loop and not target_loop.is_closed():
            if running_loop is target_loop:
                target_loop.create_task(manager.broadcast(msg))
            else:
                asyncio.run_coroutine_threadsafe(manager.broadcast(msg), target_loop)
    except Exception as exc:
        logger.error("Failed to broadcast alert: %s", exc)


app = FastAPI(title="S.P.A.R.K. Bridge API")

# --- Middlewares ---

# 1. CORS Configuration
_cors_origins_raw = os.getenv("SPARK_CORS_ORIGINS", "*")
_cors_origins = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]
if not _cors_origins:
    _cors_origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 2. IP Restriction Middleware (Production Security Safeguard)
@app.middleware("http")
async def ip_restriction_middleware(request: Request, call_next):
    allowed_ips_raw = os.getenv("SPARK_ALLOWED_IPS", "").strip()
    if allowed_ips_raw:
        client_ip = request.client.host if request.client else None
        # Always allow local loopback
        if client_ip not in {"127.0.0.1", "::1", "localhost", "testclient"}:
            allowed_ips = [ip.strip() for ip in allowed_ips_raw.split(",") if ip.strip()]
            if client_ip not in allowed_ips:
                logger.warning("Access blocked from unauthorized IP address: %s", client_ip)
                return JSONResponse(
                    status_code=403, content={"error": "IP address access restricted"}
                )
    return await call_next(request)


# --- Lifecycle Events ---
@app.on_event("startup")
async def startup_tasks():
    logger.info("Initializing S.P.A.R.K. Bridge API startup sequence...")
    await execute_startup_sequence(vitals_router, manager.broadcast)
    logger.info("S.P.A.R.K. Bridge API is online and listening.")


@app.on_event("shutdown")
async def shutdown_tasks():
    logger.info("Initiating S.P.A.R.K. Bridge API shutdown sequence...")
    await execute_shutdown_sequence(vitals_router)
    logger.info("S.P.A.R.K. Bridge API successfully shut down.")


# --- Exception Handlers ---
@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    if exc.status_code == 401:
        return JSONResponse(status_code=401, content={"error": "unauthorized"})
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": str(exc.detail) if exc.detail else "error"},
    )


# --- Register Routers ---
app.include_router(auth_router)
app.include_router(chat_router)
app.include_router(override_router)
app.include_router(websockets_router)

app.include_router(memory_router)
app.include_router(projects_router)
app.include_router(personal_router)
app.include_router(task_router)
app.include_router(runtime_router)
app.include_router(security_router)
app.include_router(satellite_router)
app.include_router(biometric_router)

# Mount Static Files (must be mounted after API routes to avoid catching routing patterns)
STATIC_DIR = os.path.join(BASE_DIR, "api", "static")
if not os.path.exists(STATIC_DIR):
    os.makedirs(STATIC_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# --- Root & Base Status Endpoints ---
@app.get("/ping")
async def ping():
    return {"status": "online", "version": "SPARK-1.0"}


@app.get("/", response_class=HTMLResponse)
async def get_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(index_path):
        return HTMLResponse("<h1>S.P.A.R.K. Static Interface not found</h1>", status_code=404)
    with open(index_path, "r", encoding="utf-8") as index_file:
        return HTMLResponse(index_file.read())


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/status", dependencies=[Depends(verify_token), Depends(rate_limit)])
@app.get("/api/status", dependencies=[Depends(verify_token), Depends(rate_limit)])
async def status():
    return {"status": "ok", "service": "S.P.A.R.K"}


@app.get("/memory", dependencies=[Depends(verify_token), Depends(rate_limit)])
async def get_memory_stats():
    from core.spark_brain import memory as spark_memory

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


@app.post("/internal/broadcast")
async def broadcast_event(request: Request):
    """Webhook for core/main.py to propagate events (voice, logs, system alerts) to HUD."""
    try:
        data = await request.json()
        await manager.broadcast(data)
        return {"status": "ok"}
    except Exception as exc:
        logger.error("Internal broadcast webhook failed: %s", exc)
        return JSONResponse(status_code=400, content={"error": "invalid_payload"})
