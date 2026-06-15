"""Dashboard Server — FastAPI + WebSocket backend for JARVIS dashboard."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.web.server")

DASHBOARD_DIR = Path(__file__).parent / "dashboard"


def create_app(spark_os=None):
    """Create FastAPI app for the dashboard."""
    try:
        from fastapi import FastAPI, WebSocket, WebSocketDisconnect
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import FileResponse
    except ImportError:
        logger.error("FastAPI not installed: pip install fastapi uvicorn")
        return None

    app = FastAPI(title="SPARK Dashboard", version="2.0.0")
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

    _connections: list[WebSocket] = []

    @app.get("/")
    async def serve_index():
        index_path = DASHBOARD_DIR / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        return {"error": "Dashboard not found"}

    @app.get("/api/status")
    async def get_status():
        if spark_os:
            return spark_os.dashboard_snapshot()
        return {"status": "no_spark_instance"}

    @app.get("/api/goals")
    async def get_goals():
        if spark_os:
            return spark_os.goal_engine.stats()
        return {}

    @app.get("/api/memory")
    async def get_memory():
        if spark_os:
            return {
                "semantic": spark_os.semantic_memory.count(),
                "episodic": spark_os.episodic_memory.count(),
                "working": spark_os.working_memory.snapshot(),
            }
        return {}

    @app.get("/api/agents")
    async def get_agents():
        if spark_os:
            return [
                a.info() for a in [
                    spark_os.planner_agent, spark_os.executor_agent,
                    spark_os.memory_agent, spark_os.reflection_agent,
                    spark_os.observer_agent,
                ]
            ]
        return []

    @app.get("/api/awareness")
    async def get_awareness():
        if spark_os:
            return {
                "feed": spark_os.awareness_bus.recent(limit=20),
                "world_model": spark_os.world_model.snapshot(),
                "context": spark_os.context.snapshot(),
            }
        return {}

    @app.get("/api/decisions")
    async def get_decisions():
        if spark_os:
            return spark_os.decision_log.recent(limit=50)
        return []

    @app.get("/api/skills")
    async def get_skills():
        if spark_os:
            return spark_os.skill_registry.list_all()
        return []

    @app.get("/api/capabilities")
    async def get_capabilities():
        if spark_os:
            return spark_os.capability_registry.list_all()
        return []

    @app.get("/api/health")
    async def get_health():
        if spark_os:
            return spark_os.env_awareness.get_health()
        return {}

    @app.post("/api/command")
    async def post_command(body: dict[str, Any]):
        if spark_os:
            result = await spark_os.process(body.get("input", ""), source="api")
            return result
        return {"error": "no_spark_instance"}

    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await websocket.accept()
        _connections.append(websocket)
        try:
            while True:
                if spark_os:
                    snapshot = spark_os.dashboard_snapshot()
                    await websocket.send_json(snapshot)
                await asyncio.sleep(2)
        except WebSocketDisconnect:
            _connections.remove(websocket)
        except Exception:
            if websocket in _connections:
                _connections.remove(websocket)

    app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR)), name="static")

    return app


class DashboardServer:
    def __init__(self, spark_os=None, host: str = "0.0.0.0", port: int = 8080) -> None:
        self._spark_os = spark_os
        self._host = host
        self._port = port
        self._app = None

    def start(self) -> None:
        self._app = create_app(self._spark_os)
        if self._app:
            import uvicorn
            uvicorn.run(self._app, host=self._host, port=self._port)

    @property
    def app(self):
        return self._app
