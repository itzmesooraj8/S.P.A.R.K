"""S.P.A.R.K. API Signal Override and HUD Serve Router."""

from __future__ import annotations

import logging
import os
import time

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from fastapi.responses import HTMLResponse

from api.auth import validate_access_token_or_static, verify_token
from api.routes.chat import rate_limit
from api.routes.websockets import manager

logger = logging.getLogger("SPARK_OVERRIDE_ROUTES")

router = APIRouter(tags=["override"])

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
STATIC_DIR = os.path.join(BASE_DIR, "api", "static")
HUD_MOBILE_PATH = os.path.join(BASE_DIR, "hud", "mobile.html")


@router.get("/override", response_class=HTMLResponse)
async def get_override():
    """Serves the mobile Signal Override UI (no auth required for discovery)."""
    override_path = os.path.join(STATIC_DIR, "override.html")
    if not os.path.exists(override_path):
        return HTMLResponse("<h1>Signal Override not configured</h1>", status_code=404)
    with open(override_path, "r", encoding="utf-8") as override_file:
        return HTMLResponse(override_file.read())


@router.get("/mobile", response_class=HTMLResponse)
async def get_mobile_public():
    """Serves the public mobile interface page."""
    if not os.path.exists(HUD_MOBILE_PATH):
        return HTMLResponse("<h1>SPARK mobile HUD not found</h1>", status_code=404)
    with open(HUD_MOBILE_PATH, "r", encoding="utf-8") as mobile_file:
        return HTMLResponse(mobile_file.read())


@router.get("/hud", response_class=HTMLResponse, dependencies=[Depends(verify_token)])
async def get_hud_mobile():
    """Serves the authenticated mobile HUD page (requires active Bearer auth)."""
    if not os.path.exists(HUD_MOBILE_PATH):
        return HTMLResponse("<h1>SPARK mobile HUD not found</h1>", status_code=404)
    with open(HUD_MOBILE_PATH, "r", encoding="utf-8") as mobile_file:
        return HTMLResponse(mobile_file.read())


@router.post("/api/override/cast", dependencies=[Depends(rate_limit)])
async def cast_signal_override(request: Request, x_spark_token: str = Header(None)):
    """Remote Signal Override: cast to any display running SPARK HUD.

    Requires X-SPARK-TOKEN header matching SPARK_TOKEN.
    Broadcasts signal_override event to all connected WebSocket clients.
    """
    if not validate_access_token_or_static(x_spark_token or ""):
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        body = await request.json()
        target_url = body.get("target_url", "localhost:8000")
        payload = body.get("payload", {})
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid payload")

    # Broadcast Signal Override event to all connected HUD clients
    await manager.broadcast(
        {
            "type": "signal_override",
            "target_url": target_url,
            "payload": payload,
            "timestamp": time.time(),
        }
    )

    return {"status": "signal cast", "clients_notified": len(manager.active_connections)}
