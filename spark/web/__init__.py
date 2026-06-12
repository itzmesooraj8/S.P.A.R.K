"""
Spark Web — Web Dashboard Backend

FastAPI + WebSocket for real-time JARVIS dashboard.
"""

from spark.web.server import create_app, DashboardServer

__all__ = ["create_app", "DashboardServer"]
