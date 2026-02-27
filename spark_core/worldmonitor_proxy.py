"""
WorldMonitor API Proxy Router
==============================
Proxies all WorldMonitor-specific API calls to the WorldMonitor dev server
(default: http://localhost:8081, configurable via WORLDMONITOR_URL env var).

Handles:
  GET  /api/rss-proxy
  GET  /api/opensky
  GET  /api/ais-snapshot
  GET  /api/polymarket
  POST /api/{domain}/v1/{rpc}   (all WorldMonitor sebuf RPC routes)

These paths exist only in the WorldMonitor's own Vite server — the SPARK
FastAPI backend needs to forward them to avoid 404 / 405 flood.
"""

import os
import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

# Where the WorldMonitor standalone dev server is running.
# spawnWorldMonitorPlugin() in vite.config.ts starts it on port 3000 (WM default).
# Override with WORLDMONITOR_URL env var if needed.
WORLDMONITOR_BASE = os.getenv("WORLDMONITOR_URL", "http://localhost:3000").rstrip("/")

# WorldMonitor RPC domains (must match the worldmonitor routing)
WM_DOMAINS = {
    "intelligence", "military", "economic", "market", "conflict",
    "research", "unrest", "climate", "wildfire", "displacement",
    "infrastructure", "supply-chain", "trade", "giving", "prediction",
    "aviation", "maritime", "cyber", "seismology", "positive-events",
    "news", "security",
}

router = APIRouter()


async def _forward(request: Request, upstream_path: str) -> Response:
    """
    Forward a request to the WorldMonitor server and relay the response.
    Propagates query string, body, and safe request headers.
    """
    query = str(request.url.query)
    target = f"{WORLDMONITOR_BASE}/{upstream_path}"
    if query:
        target = f"{target}?{query}"

    # Safe headers to forward (skip hop-by-hop and host)
    SKIP_REQ_HEADERS = {"host", "connection", "transfer-encoding", "upgrade", "keep-alive"}
    fwd_headers = {
        k: v for k, v in request.headers.items()
        if k.lower() not in SKIP_REQ_HEADERS
    }

    body = await request.body()

    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            upstream = await client.request(
                method=request.method,
                url=target,
                headers=fwd_headers,
                content=body or None,
            )

        # Drop headers that would confuse FastAPI's response stack
        SKIP_RESP_HEADERS = {"transfer-encoding", "content-encoding", "content-length"}
        resp_headers = {
            k: v for k, v in upstream.headers.items()
            if k.lower() not in SKIP_RESP_HEADERS
        }
        resp_headers["Access-Control-Allow-Origin"] = "*"

        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            headers=resp_headers,
            media_type=upstream.headers.get("content-type"),
        )

    except httpx.ConnectError:
        return JSONResponse(
            {
                "error": "WorldMonitor server unavailable",
                "detail": f"Cannot reach {WORLDMONITOR_BASE}. Start the WorldMonitor dev server (npm run dev inside external/worldmonitor).",
            },
            status_code=503,
        )
    except httpx.TimeoutException:
        return JSONResponse({"error": "WorldMonitor server timed out"}, status_code=504)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": "Proxy error", "detail": str(exc)}, status_code=502)


# ---------------------------------------------------------------------------
# Simple GET proxy routes
# ---------------------------------------------------------------------------

@router.api_route("/api/rss-proxy", methods=["GET", "OPTIONS"])
async def proxy_rss(request: Request) -> Response:
    if request.method == "OPTIONS":
        return Response(status_code=204, headers={"Access-Control-Allow-Origin": "*",
                                                   "Access-Control-Allow-Methods": "GET, OPTIONS"})
    return await _forward(request, "api/rss-proxy")


@router.api_route("/api/opensky", methods=["GET", "OPTIONS"])
async def proxy_opensky(request: Request) -> Response:
    if request.method == "OPTIONS":
        return Response(status_code=204, headers={"Access-Control-Allow-Origin": "*"})
    return await _forward(request, "api/opensky")


@router.api_route("/api/ais-snapshot", methods=["GET", "OPTIONS"])
async def proxy_ais(request: Request) -> Response:
    if request.method == "OPTIONS":
        return Response(status_code=204, headers={"Access-Control-Allow-Origin": "*"})
    return await _forward(request, "api/ais-snapshot")


@router.api_route("/api/polymarket", methods=["GET", "OPTIONS"])
async def proxy_polymarket(request: Request) -> Response:
    if request.method == "OPTIONS":
        return Response(status_code=204, headers={"Access-Control-Allow-Origin": "*"})
    return await _forward(request, "api/polymarket")


# ---------------------------------------------------------------------------
# WorldMonitor sebuf RPC catch-all:  /api/{domain}/v1/{rpc}
# ---------------------------------------------------------------------------

@router.api_route(
    "/api/{domain}/v1/{rpc}",
    methods=["POST", "GET", "OPTIONS"],
)
async def proxy_wm_rpc(domain: str, rpc: str, request: Request) -> Response:
    """
    Catch-all proxy for WorldMonitor sebuf RPC routes.
    Only forwards requests whose domain is a known WorldMonitor domain.
    Everything else falls through to a 404 so SPARK's own routes are unaffected.
    """
    if request.method == "OPTIONS":
        return Response(
            status_code=204,
            headers={
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type, Authorization",
            },
        )

    if domain not in WM_DOMAINS:
        return JSONResponse({"error": f"Unknown domain: {domain}"}, status_code=404)

    return await _forward(request, f"api/{domain}/v1/{rpc}")
