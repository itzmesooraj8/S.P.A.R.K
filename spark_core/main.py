import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import time
import sys
import json
from contextlib import asynccontextmanager
from typing import Optional, List

from ws.manager import ws_manager
from orchestrator.brain import AIOrchestrator
from system.monitor import SystemMonitor
from tools.sandbox import init_sandbox, teardown_sandbox
from intelligence.registry import project_registry
from intelligence.cross_analyzer import cross_analyzer
from intelligence.pattern_memory import pattern_store
from intelligence.optimizer import optimizer
from intelligence.trust_layer import trust_store
from globe_api import router as globe_api_router, globe_broadcaster

# ── SPARK OS — New Systems ─────────────────────────────────────────────────────
from auth.jwt_handler import create_token_pair, refresh_access_token, require_auth, ACCESS_TOKEN_TTL
from auth.user_store import authenticate, list_users, create_user
from llm.model_router import model_router
from agents.commander import commander
from agents.spark_commander_router import commander_router, classify_intent
from cognitive.loop import cognitive_loop
from cognitive.self_optimizer import self_evolution
from memory.graph_memory import knowledge_graph
from globe.predictor import threat_predictor

# ── NEW SPARK FEATURE MODULES ──────────────────────────────────────────────────
from voice.tts_router import tts_router
from neural_search.search import neural_router
from plugins.manager import plugins_router
from scheduler_service import scheduler_router, init_scheduler
from agents.browser_agent import browser_router

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Initialize Core Services
orchestrator = AIOrchestrator()
sys_monitor = SystemMonitor()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🛸 [SPARK] Sovereign AI OS Initializing...")

    # Auto-Bootstrap Single Root Workspace
    workspace_root = os.path.dirname(os.path.dirname(__file__))
    project_registry.load_project("workspace", workspace_root)
    project_registry.switch_focus("workspace")

    # Log the exact workspace path that will be used for scanning:
    from pathlib import Path as _Path
    _container_ws = "/workspace" if _Path("/workspace").exists() else None
    effective_workspace = os.getenv("SPARK_WORKSPACE_DIR", _container_ws or workspace_root)
    print(f"📂 [SPARK] Workspace root   : {workspace_root}")
    print(f"📂 [SPARK] Effective scanner path: {effective_workspace}")
    if os.getenv("SPARK_WORKSPACE_DIR"):
        print(f"📂 [SPARK] Source: SPARK_WORKSPACE_DIR env var")
    elif _container_ws:
        print(f"📂 [SPARK] Source: /workspace container mount")
    else:
        print(f"📂 [SPARK] Source: project root (host mode)")

    # Initialize the sandbox isolated execution environment
    from tools.sandbox import sandbox
    sandbox.host_workspace_dir = effective_workspace
    await init_sandbox()

    # ── Boot SPARK OS systems ──────────────────────────────────────────────
    # Knowledge Graph Memory
    await knowledge_graph.init()
    print("🧠 [SPARK] Knowledge graph memory online.")

    # Start background intelligence loop
    asyncio.create_task(sys_monitor.start_monitoring(ws_manager))
    print("✅ [SPARK] Background monitor started.")

    # Start Globe WebSocket push broadcaster (every 30s)
    globe_broadcaster.start()
    print("🌍 [SPARK] Globe WS broadcaster started.")

    # Start Autonomous Cognitive Loop
    cognitive_loop.start()
    print("🔮 [SPARK] Cognitive loop started.")

    # ── Start APScheduler for reminders/tasks ───────────────────────────────
    init_scheduler()
    print("⏰ [SPARK] Task scheduler initialized.")

    # ── Start all registered agents (deferred from import time) ─────────────
    await commander.startup()
    print("🎖️  [SPARK] Commander agents online.")

    # ── Auto-index knowledge base into ChromaDB ─────────────────────────────
    try:
        from neural_search.search import get_collection
        import os as _os
        kb_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "knowledge_base")
        if _os.path.exists(kb_path):
            collection = get_collection("spark_knowledge")
            count = collection.count()
            if count == 0:
                print("🧠 [NeuralSearch] Knowledge base not yet indexed — running auto-index...")
                import asyncio as _asyncio
                _asyncio.create_task(_auto_index_kb())
            else:
                print(f"🧠 [NeuralSearch] ChromaDB ready — {count} docs in spark_knowledge.")
    except Exception as e:
        print(f"⚠️ [NeuralSearch] ChromaDB init warning: {e}")

    # Start threat predictor feed task (polls globe data every 5 min)
    asyncio.create_task(_threat_feed_loop())
    print("⚠️  [SPARK] Threat predictor feed started.")

    # Log active models
    asyncio.create_task(_log_model_status())

    print("🛸 [SPARK] All systems online. Sovereign AI OS ready.")

    yield

    print("🛸 [SPARK] Core Node Shutting Down...")
    cognitive_loop.stop()
    await teardown_sandbox()


async def _log_model_status():
    """Log available models at startup (non-blocking)."""
    await asyncio.sleep(5)
    try:
        status = await model_router.get_status()
        available = [m["name"] for m in status["models"] if m["available"]]
        print(f"🧬 [ModelRouter] Available models: {available}")
    except Exception:
        pass


async def _auto_index_kb():
    """Auto-index knowledge base documents into ChromaDB on first boot."""
    await asyncio.sleep(10)  # Let everything else start first
    try:
        import os as _os, time as _time, uuid as _uuid
        from neural_search.search import get_collection
        kb_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "knowledge_base")
        if not _os.path.exists(kb_path):
            return
        collection = get_collection("spark_knowledge")
        indexed = 0
        for fname in _os.listdir(kb_path):
            fpath = _os.path.join(kb_path, fname)
            if not _os.path.isfile(fpath):
                continue
            try:
                with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read().strip()
                if not text:
                    continue
                doc_id = f"kb:{fname}"
                collection.upsert(
                    ids=[doc_id],
                    documents=[text],
                    metadatas=[{"source": "knowledge_base", "filename": fname, "indexed_at": _time.time()}],
                )
                indexed += 1
            except Exception as e:
                print(f"⚠️ [NeuralSearch] Failed to index {fname}: {e}")
        print(f"🧠 [NeuralSearch] Auto-indexed {indexed} knowledge base documents.")
    except Exception as e:
        print(f"⚠️ [NeuralSearch] Auto-index failed: {e}")


async def _threat_feed_loop():
    """
    Background task: fetch globe events every 5 minutes
    and feed them to the threat predictor for risk analysis.
    """
    await asyncio.sleep(60)  # Wait for globe broadcaster to warm up
    while True:
        try:
            async with __import__("httpx").AsyncClient(timeout=15.0) as c:
                # Feed earthquake data
                eq_r = await c.get("http://localhost:8000/api/seismology/v1/listEarthquakes",
                                   json={"layers": ["earthquake"]}, timeout=15.0)
                if eq_r.status_code == 200:
                    events = eq_r.json().get("events", [])
                    threat_predictor.ingest(events, "earthquake")

                # Feed conflict data
                cf_r = await c.post("http://localhost:8000/api/conflict/v1/listConflictEvents",
                                    json={"layers": ["conflict"]}, timeout=15.0)
                if cf_r.status_code == 200:
                    events = cf_r.json().get("events", [])
                    threat_predictor.ingest(events, "conflict")

                # Feed wildfire data
                wf_r = await c.post("http://localhost:8000/api/wildfire/v1/listFireDetections",
                                    json={"layers": ["fires"]}, timeout=15.0)
                if wf_r.status_code == 200:
                    events = wf_r.json().get("detections", [])
                    threat_predictor.ingest(events, "fire")

            # Inject threat summary into cognitive loop for awareness
            summary = threat_predictor.get_global_threat_summary()
            cognitive_loop.inject_observation({
                "globe_threat_summary": summary,
                "global_risk_score": summary.get("global_risk_score", 0),
                "global_risk_level": summary.get("global_risk_level", "LOW"),
                "hotspots": summary.get("hotspots", 0),
            })

        except Exception as exc:
            print(f"⚠️  [ThreatFeed] Error: {exc}")

        await asyncio.sleep(300)  # 5 minutes


app = FastAPI(title="SPARK AI Core v2", version="2.0.0", lifespan=lifespan)

# CORS for local dev HUD
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Globe Intelligence API (handles /api/seismology, /api/conflict, /api/market, etc.)
# Must be registered BEFORE the static-file catch-all.
app.include_router(globe_api_router)

# ── New SPARK Feature Routers ─────────────────────────────────────────────────
app.include_router(tts_router)      # /api/voice/*   — TTS + WS audio
app.include_router(neural_router)   # /api/neural-search/* — ChromaDB semantic search
app.include_router(plugins_router)  # /api/plugins/*  — plugin enable/disable
app.include_router(scheduler_router)# /api/scheduler/* — reminders + cron jobs
app.include_router(browser_router)  # /api/browser/*  — Playwright web agent

# -----------------
# API ENDPOINTS
# -----------------

from system.event_bus import event_bus

# -----------------
# VERSION & CONFIG
# -----------------

@app.get("/api/version")
async def api_version():
    """Return SPARK version and build info."""
    return {
        "version": "3.0.0",
        "codename": "SOVEREIGN",
        "api_schema_version": 1,
        "build_date": "2026-03-01",
    }

@app.get("/api/config/status")
async def api_config_status():
    """Which providers are configured, key presence, degraded-mode flags."""
    import os as _os
    def _key_present(env: str) -> bool:
        return bool(_os.getenv(env))

    # Load secrets.yaml for key detection without exposing values
    yaml_keys: dict = {}
    try:
        import yaml as _yaml
        _cfg_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), "config", "secrets.yaml")
        if _os.path.exists(_cfg_path):
            with open(_cfg_path) as _f:
                yaml_keys = _yaml.safe_load(_f) or {}
    except Exception:
        pass

    def _yaml_key(k: str) -> bool:
        return bool(yaml_keys.get(k))

    providers = {
        "ollama": {
            "enabled": True,  # always available locally
            "base_url": _os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        },
        "openai": {
            "key_set": _key_present("OPENAI_API_KEY") or _yaml_key("openai_api_key"),
            "degraded": not (_key_present("OPENAI_API_KEY") or _yaml_key("openai_api_key")),
        },
        "anthropic": {
            "key_set": _key_present("ANTHROPIC_API_KEY") or _yaml_key("anthropic_api_key"),
            "degraded": not (_key_present("ANTHROPIC_API_KEY") or _yaml_key("anthropic_api_key")),
        },
        "google": {
            "key_set": _key_present("GOOGLE_API_KEY") or _yaml_key("google_api_key"),
            "degraded": not (_key_present("GOOGLE_API_KEY") or _yaml_key("google_api_key")),
        },
        "nasa_firms": {
            "key_set": _key_present("NASA_FIRMS_API_KEY") or _yaml_key("nasa_firms_api_key"),
        },
    }

    degraded = [k for k, v in providers.items() if v.get("degraded")]

    return {
        "providers": providers,
        "degraded_providers": degraded,
        "degraded_mode": len(degraded) > 0,
        "jwt_secret_from_env": _key_present("SPARK_JWT_SECRET"),
    }

# -----------------
# TOOLS REGISTRY
# -----------------

@app.get("/api/tools")
async def list_tools():
    """Returns the registry of available tools with names, descriptions, and risk levels."""
    try:
        registry = orchestrator.router.registry
        tool_list = []
        for name, tool_def in registry.tools.items():
            tool_list.append({
                "name": name,
                "description": tool_def.description or (tool_def.handler.__doc__ if tool_def.handler else "No description"),
                "risk_level": tool_def.risk_level.name,
            })
        return {"tools": tool_list, "count": len(tool_list)}
    except Exception as e:
        return {"error": str(e), "tools": [], "count": 0}

# -----------------
# WEBSOCKET NAMESPACES
# -----------------

@app.websocket("/ws/ai")
async def websocket_ai(websocket: WebSocket):
    await ws_manager.connect(websocket, "ai")
    session_id = str(id(websocket))
    ws_manager.register_session(session_id, websocket)
    try:
        while True:
            raw_data = await websocket.receive_text()
            
            import json
            try:
                msg = json.loads(raw_data)
                if msg.get("type") == "CANCEL":
                    event_bus.publish("cancel_task", {})
                    continue
            except json.JSONDecodeError:
                pass
            
            # Transport only: No intelligence inside WebSocket handler
            # Only publish "user_input"
            event_bus.publish("user_input", {"data": raw_data, "websocket": websocket, "session_id": session_id})
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "ai")

@app.websocket("/ws/system")
async def websocket_system(websocket: WebSocket):
    await ws_manager.connect(websocket, "system")
    try:
        while True:
            raw = await websocket.receive_text()
            # Respond to ping frames to keep connection alive
            try:
                frame = json.loads(raw)
                if frame.get("type") == "PING":
                    await websocket.send_text(json.dumps({"v": 1, "type": "PONG", "ts": time.time() * 1000}))
            except (json.JSONDecodeError, Exception):
                pass
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "system")

@app.websocket("/ws/globe")
async def websocket_globe(websocket: WebSocket):
    """Real-time Globe Intelligence push channel.
    Server messages:
      GLOBE_DELTA   — new/updated events for a specific layer
      GLOBE_TICKER  — market/financial tick updates
      GLOBE_FUSION  — Signal Fusion alerts
      GLOBE_HEALTH  — provider health summary
    """
    await websocket.accept()
    globe_broadcaster.add_client(websocket)
    try:
        # Trigger an immediate push cycle so the client gets data on connect
        await globe_broadcaster._push_cycle()
        while True:
            # Keep the connection alive; client may send ping or layer-toggle messages
            data = await websocket.receive_text()
            # Honour explicit client ping
            if data.strip() == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        globe_broadcaster.remove_client(websocket)
    except Exception:
        globe_broadcaster.remove_client(websocket)

# EventBus subscribers to handle outward flow (Forward response_token back)
@event_bus.subscribe("response_token")
async def handle_response_token(payload):
    token = payload.get("token")
    session_id = payload.get("session_id")
    if token is not None:
        data = {"type": "TOKEN", "content": token}
        if session_id:
            # Route to the specific client that owns this session
            await ws_manager.send_to_session(session_id, data)
        else:
            # Fallback: broadcast to all AI subscribers (e.g. tool reflection path)
            await ws_manager.broadcast_json(data, "ai")

@event_bus.subscribe("response_done")
async def handle_response_done(payload):
    session_id = payload.get("session_id")
    data = {"type": "DONE"}
    if session_id:
        await ws_manager.send_to_session(session_id, data)
    else:
        await ws_manager.broadcast_json(data, "ai")

@event_bus.subscribe("confirm_tool")
async def handle_confirm_tool(payload):
    await ws_manager.broadcast_json({
        "type": "CONFIRM_TOOL",
        **payload
    }, "system")


@event_bus.subscribe("spark_alert")
async def handle_spark_alert(payload):
    """Forward cognitive loop alerts to all connected /ws/system clients."""
    await ws_manager.broadcast_json({
        "v": 1,
        "type": "ALERT",
        "ts": time.time() * 1000,
        "severity": payload.get("severity", "info"),
        "title": payload.get("title", "SPARK Alert"),
        "body": payload.get("body", payload.get("message", "")),
        "source": payload.get("source", "cognitive_loop"),
    }, "system")


# -----------------
# API ENDPOINTS
# -----------------
class AuthRequest(BaseModel):
    username: str
    password: str

class RefreshRequest(BaseModel):
    refresh_token: str

class CreateUserRequest(BaseModel):
    username: str
    password: str
    role: str = "OPERATOR"

@app.post("/api/auth/login")
async def login(req: AuthRequest):
    """Authenticate and return access + refresh token pair."""
    user = authenticate(req.username, req.password)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid credentials")
    tokens = create_token_pair(user["sub"], user["role"])
    raw_role = user["role"].upper()
    fe_role = "admin" if raw_role in ("ROOT", "ADMIN") else ("viewer" if raw_role == "VIEWER" else "operator")
    tokens["expires_in"] = ACCESS_TOKEN_TTL
    tokens["user"] = {"username": user["sub"], "role": fe_role}
    return tokens

@app.post("/api/auth/refresh")
async def refresh_token(req: RefreshRequest):
    """Exchange refresh token for a new access token."""
    result = refresh_access_token(req.refresh_token)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="Invalid or expired refresh token")
    result["expires_in"] = ACCESS_TOKEN_TTL
    return result

@app.post("/api/auth/logout")
async def logout(req: RefreshRequest):
    """Revoke refresh token."""
    from auth.jwt_handler import revoke_refresh_token
    revoked = revoke_refresh_token(req.refresh_token)
    return {"status": "ok" if revoked else "not_found"}

@app.get("/api/auth/users", dependencies=[Depends(require_auth("ADMIN"))])
async def get_users():
    """List all users (admin only)."""
    return {"users": list_users()}

@app.post("/api/auth/users", dependencies=[Depends(require_auth("ROOT"))])
async def add_user(req: CreateUserRequest):
    """Create a new user (root only)."""
    success = create_user(req.username, req.password, req.role)
    if not success:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="Username already exists")
    return {"status": "created", "username": req.username, "role": req.role}

@app.get("/api/state")
async def get_state():
    return orchestrator.get_state()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# AGENT ENDPOINTS — Multi-agent Command & Control
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AgentDispatchRequest(BaseModel):
    task_type: str
    payload: dict
    session_id: Optional[str] = None
    wait: bool = False
    timeout: float = 30.0

@app.get("/api/agents/status")
async def agents_status():
    """Live status of all SPARK sub-agents."""
    return commander.get_status()

@app.post("/api/agents/dispatch")
async def agents_dispatch(req: AgentDispatchRequest):
    """Dispatch a task to a specific agent and optionally await result."""
    result = await commander.dispatch(
        task_type=req.task_type,
        payload=req.payload,
        session_id=req.session_id,
        wait=req.wait,
        timeout=req.timeout,
    )
    if result:
        return {"success": result.success, "output": result.output,
                "agent": result.agent_name, "confidence": result.confidence,
                "error": result.error}
    return {"status": "queued", "task_type": req.task_type}

class AskRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    wait: bool = False

@app.post("/api/agents/ask")
async def agents_ask(req: AskRequest):
    """Natural-language task routing through Commander."""
    result = await commander.ask(req.text, session_id=req.session_id, wait=req.wait)
    if result:
        return {"success": result.success, "output": result.output,
                "agent": result.agent_name, "confidence": result.confidence}
    return {"status": "queued"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COMMANDER ROUTER — JARVIS-style intent routing + Action Feed
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CommanderRunRequest(BaseModel):
    text: str
    session_id: Optional[str] = None
    context_snapshot: Optional[dict] = None

@app.post("/api/commander/run")
async def commander_run(req: CommanderRunRequest):
    """
    JARVIS Command entry-point.
    Classifies intent, builds plan, emits PLAN→STEP WS frames, executes.
    """
    result = await commander_router.run(
        text=req.text,
        context_snapshot=req.context_snapshot,
        session_id=req.session_id,
    )
    return result

@app.get("/api/commander/context")
async def commander_context():
    """Returns current SPARK state snapshot for the frontend to attach to commands."""
    from system.state import unified_state
    state = unified_state.get_state()
    metrics = state.get("metrics", {})
    return {
        "spark_version": "2.0.0",
        "active_agents":  [name for name, ag in commander.get_status().get("agents", {}).items()
                           if ag.get("queue_size", 0) > 0 or ag.get("status") == "running"],
        "metrics": {
            "cpu":     metrics.get("cpu_percent", 0),
            "ram":     metrics.get("memory_percent", 0),
            "ping_ms": metrics.get("ping_ms", 0),
        },
        "threat_level": state.get("threat_level", "low"),
        "ts": time.time(),
    }


# ── SPARK Routines — named operating-mode sequences ───────────────────────────

@app.post("/api/commander/routine/{name}")
async def run_routine(name: str):
    """
    Activate a named SPARK routine (dev / monitor / focus).
    Builds a Plan from the routine's step sequence, emits PLAN/STEP WS frames,
    executes each step (open_app, open_url, run_command, frontend_fx, emit_alert).
    """
    import uuid
    from agents.routines import get_routine, list_routines
    from agents.spark_commander_router import (
        Plan, PlanStep, Intent, execute_plan, emit_plan,
    )

    routine = get_routine(name)
    if not routine:
        raise HTTPException(
            status_code=404,
            detail=f"Routine '{name}' not found. Available: {list_routines()}",
        )

    plan = Plan(
        plan_id=str(uuid.uuid4()),
        intent=Intent.TASK,
        query=f"routine:{name}",
        ts=time.time(),
    )
    plan.steps = [
        PlanStep(
            idx=i,
            label=s["label"],
            tool=s.get("tool"),
            args=s.get("args", {}),
        )
        for i, s in enumerate(routine.steps)
    ]

    await emit_plan(plan)
    result = await execute_plan(plan)

    return {
        "routine":  name,
        "name":     routine.name,
        "plan_id":  plan.plan_id,
        "steps":    [{"idx": s.idx, "label": s.label, "status": s.status.value, "result": s.result}
                     for s in plan.steps],
        "result":   result,
    }


@app.get("/api/commander/routines")
async def list_available_routines():
    """Returns all registered SPARK routines with their names and descriptions."""
    from agents.routines import ROUTINES
    return {k: {"name": v.name, "description": v.description} for k, v in ROUTINES.items()}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODEL ROUTER — Intelligence Model Management
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/models/status")
async def models_status():
    """Live status of all connected LLM providers."""
    return await model_router.get_status()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# COGNITIVE ENGINE — Autonomous Reasoning Loop
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/cognitive/status")
async def cognitive_status():
    """Current state of the autonomous cognitive loop."""
    return cognitive_loop.get_status()

@app.post("/api/cognitive/inject")
async def cognitive_inject(data: dict):
    """Inject an external observation into the cognitive loop."""
    cognitive_loop.inject_observation(data)
    return {"status": "injected"}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# KNOWLEDGE GRAPH — Long-Term Strategic Memory
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class EntityRequest(BaseModel):
    type: str
    name: str
    properties: dict = {}
    importance: float = 1.0

class RelationRequest(BaseModel):
    source_id: str
    target_id: str
    relation_type: str
    weight: float = 1.0
    properties: dict = {}

class ObservationRequest(BaseModel):
    content: str
    entity_id: Optional[str] = None
    session_id: Optional[str] = None
    importance: float = 1.0
    tags: List[str] = []

@app.get("/api/memory/stats")
async def memory_stats():
    """Knowledge graph statistics."""
    stats = await knowledge_graph.get_stats()
    return stats

@app.get("/api/memory/search")
async def memory_search(q: str, type: Optional[str] = None, limit: int = 20):
    """Search entities in the knowledge graph."""
    return {"results": await knowledge_graph.search_entities(q, entity_type=type, limit=limit)}

@app.post("/api/memory/entity")
async def memory_add_entity(req: EntityRequest):
    eid = await knowledge_graph.upsert_entity(req.type, req.name, req.properties, req.importance)
    return {"entity_id": eid}

@app.post("/api/memory/relation")
async def memory_add_relation(req: RelationRequest):
    rid = await knowledge_graph.add_relation(
        req.source_id, req.target_id, req.relation_type, req.weight, req.properties
    )
    return {"relation_id": rid}

@app.post("/api/memory/observation")
async def memory_add_observation(req: ObservationRequest):
    oid = await knowledge_graph.add_observation(
        req.content, req.entity_id, req.session_id, req.importance, req.tags
    )
    return {"observation_id": oid}

@app.get("/api/memory/observations")
async def memory_recent_observations(
    session_id: Optional[str] = None,
    limit: int = 50,
    min_importance: float = 0.0,
):
    return {"observations": await knowledge_graph.get_recent_observations(
        session_id=session_id, limit=limit, min_importance=min_importance
    )}

@app.get("/api/memory/objectives")
async def memory_objectives(status: str = "active"):
    return {"objectives": await knowledge_graph.get_objectives(status)}

class ObjectiveRequest(BaseModel):
    title: str
    description: str = ""
    priority: int = 5

@app.post("/api/memory/objectives")
async def memory_add_objective(req: ObjectiveRequest):
    oid = await knowledge_graph.upsert_objective(req.title, req.description, req.priority)
    return {"objective_id": oid}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GLOBE THREAT PREDICTOR — Predictive Intelligence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/threat/summary")
async def threat_summary():
    """Global threat assessment powered by the predictive risk engine."""
    return threat_predictor.get_global_threat_summary()

@app.get("/api/threat/regions")
async def threat_regions():
    """Per-region risk scores with escalation vectors."""
    risks = threat_predictor.get_region_risks()
    return {
        "regions": [
            {
                "id": r.region_id, "risk_score": r.risk_score, "risk_level": r.risk_level,
                "dominant_threat": r.dominant_threat, "event_count": r.event_count,
                "trend": r.trend, "hotspot": r.hotspot,
                "escalation_vectors": r.escalation_vectors,
                "lat": r.lat, "lng": r.lng,
            }
            for r in sorted(risks, key=lambda r: r.risk_score, reverse=True)
        ],
        "stats": threat_predictor.get_stats(),
    }

class IngestEventsRequest(BaseModel):
    events: List[dict]
    event_type: str = "conflict"

@app.post("/api/threat/ingest")
async def threat_ingest(req: IngestEventsRequest):
    """Feed events into the threat prediction engine."""
    threat_predictor.ingest(req.events, req.event_type)
    return {"status": "ingested", "count": len(req.events)}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SELF-EVOLUTION — Bounded Self-Improvement Engine
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/evolution/proposals")
async def evolution_proposals(status: Optional[str] = None):
    """List all self-improvement proposals."""
    from cognitive.self_optimizer import ChangeStatus
    status_enum = ChangeStatus(status) if status else None
    return {"proposals": self_evolution.get_proposals(status_enum)}

@app.post("/api/evolution/proposals/{proposal_id}/approve")
async def evolution_approve(proposal_id: str, payload: dict = Depends(require_auth("ADMIN"))):
    """Approve a self-improvement proposal (admin only)."""
    p = self_evolution.approve(proposal_id, approver=payload.get("sub", "admin"))
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Proposal not found or not PROPOSED")
    return {"status": "approved", "proposal_id": proposal_id}

@app.post("/api/evolution/proposals/{proposal_id}/reject")
async def evolution_reject(proposal_id: str, payload: dict = Depends(require_auth("ADMIN"))):
    """Reject a self-improvement proposal (admin only)."""
    p = self_evolution.reject(proposal_id, rejector=payload.get("sub", "admin"))
    if not p:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Proposal not found or not PROPOSED")
    return {"status": "rejected", "proposal_id": proposal_id}

@app.post("/api/evolution/analyze")
async def evolution_analyze():
    """Trigger self-analysis and generate improvement proposals."""
    import psutil
    metrics = {
        "memory_percent": psutil.virtual_memory().percent,
        "cpu_percent": psutil.cpu_percent(interval=0.5),
        "model_stats": {name: s.__dict__ for name, s in model_router._stats.items()},
    }
    proposals = self_evolution.analyze_and_propose(metrics)
    return {
        "proposals_generated": len(proposals),
        "proposals": [p.title for p in proposals],
    }


from globe.cases import create_case, list_cases, get_case, update_case, delete_case

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# CASES — Incident / Case Persistence
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from contracts.models import CaseItem as CaseItemModel

class CaseCreateRequest(BaseModel):
    title: str
    description: str = ""
    severity: str = "medium"
    lat: Optional[float] = None
    lng: Optional[float] = None
    layer: Optional[str] = None
    tags: List[str] = []
    meta: dict = {}

class CasePatchRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    layer: Optional[str] = None
    tags: Optional[List[str]] = None
    meta: Optional[dict] = None

@app.get("/api/globe/cases")
async def cases_list(
    severity: Optional[str] = None,
    layer: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
):
    """List saved incident cases, optionally filtered by severity or layer."""
    cases, total = await list_cases(severity=severity, layer=layer, limit=limit, offset=offset)
    return {"cases": cases, "total": total}

@app.post("/api/globe/cases", status_code=201)
async def cases_create(req: CaseCreateRequest):
    """Create a new incident case."""
    case = await create_case(
        title=req.title,
        description=req.description,
        severity=req.severity,
        lat=req.lat,
        lng=req.lng,
        layer=req.layer,
        tags=req.tags,
        meta=req.meta,
    )
    return case

@app.get("/api/globe/cases/{case_id}")
async def cases_get(case_id: str):
    from fastapi import HTTPException
    case = await get_case(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return case

@app.patch("/api/globe/cases/{case_id}")
async def cases_update(case_id: str, req: CasePatchRequest):
    from fastapi import HTTPException
    updated = await update_case(case_id, **req.model_dump(exclude_none=True))
    if not updated:
        raise HTTPException(status_code=404, detail="Case not found")
    return updated

@app.delete("/api/globe/cases/{case_id}", status_code=204)
async def cases_delete(case_id: str):
    from fastapi import HTTPException
    deleted = await delete_case(case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@app.get("/api/os/status")
async def os_status():
    """Full SPARK OS intelligence dashboard snapshot."""
    import psutil
    from cognitive.self_optimizer import ChangeStatus
    cpu = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()

    return {
        "version": "3.0.0",
        "codename": "SOVEREIGN",
        "system": {"cpu_pct": cpu, "mem_pct": mem.percent, "mem_gb": round(mem.used / 1e9, 2)},
        "cognitive_loop": cognitive_loop.get_status(),
        "agents": commander.get_status(),
        "models": await model_router.get_status(),
        "memory": await knowledge_graph.get_stats(),
        "threat": threat_predictor.get_global_threat_summary(),
        "evolution": {
            "pending_proposals": len(self_evolution.get_proposals(status=ChangeStatus.PROPOSED)),
        },
    }


@app.get("/api/health")
async def health_check():
    """Basic liveness probe."""
    return {"status": "ok", "version": "2.0.0"}

@app.get("/api/health/runtime")
async def health_runtime():
    """Read-only runtime diagnostic: sessions, queues, eventbus, scanner path."""
    from pathlib import Path as _Path
    from system.event_bus import event_bus

    # EventBus stats
    subscriber_counts = {
        evt: len(handlers)
        for evt, handlers in event_bus.subscribers.items()
    }
    active_tasks = len(event_bus.task_registry)

    # Workspace info
    from intelligence.registry import project_registry as _reg
    workspace_root = os.path.dirname(os.path.dirname(__file__))
    _container_ws = "/workspace" if _Path("/workspace").exists() else None
    effective_workspace = os.getenv("SPARK_WORKSPACE_DIR", _container_ws or workspace_root)
    workspace_source = (
        "env:SPARK_WORKSPACE_DIR" if os.getenv("SPARK_WORKSPACE_DIR")
        else ("/workspace container" if _container_ws else "host:project_root")
    )
    workspace_exists = os.path.isdir(effective_workspace)

    return {
        "event_bus": {
            "subscribers": subscriber_counts,
            "active_tasks": active_tasks,
        },
        "websocket": ws_manager.get_runtime_stats(),
        "workspace": {
            "effective_path": effective_workspace,
            "source": workspace_source,
            "exists": workspace_exists,
        },
        "projects": {
            "active": list(_reg.active_projects.keys()),
            "focus": _reg.current_focus,
        },
    }

# -----------------
# REGISTRY ENDPOINTS
# -----------------
@app.get("/api/projects/analyze")
async def analyze_cross_projects():
    """Manual trigger to process read-only meta cognition across isolated schemas"""
    return cross_analyzer.analyze_all(project_registry)

@app.get("/api/projects/optimize/{project_id}")
async def get_optimization_plan(project_id: str):
    """Phase 3A Advisory endpoint for strategic system alignment recommendations"""
    ctx = project_registry.active_projects.get(project_id)
    if not ctx:
        return {"error": "Project not active or unregistered"}, 404
        
    snap = ctx.export_snapshot()
    trends = pattern_store.compute_trends(project_id)
    
    plan = optimizer.analyze_project(project_id, snap, trends)
    return plan

class FeedbackPayload(BaseModel):
    project_id: str
    recommendation_type: str
    severity: str
    confidence: float
    user_action: int

@app.post("/api/projects/optimize/feedback")
async def submit_optimization_feedback(payload: FeedbackPayload):
    """Phase 3B endpoint capturing structured trust metrics for bounded automation readiness"""
    sev_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    sev_int = sev_map.get(payload.severity.lower(), 2)
    
    trust_store.ingest_feedback(
        project_id=payload.project_id,
        rec_type=payload.recommendation_type,
        severity=sev_int,
        confidence=payload.confidence,
        user_action=payload.user_action,
        user_weight=1.0  # Future hierarchical scaling hook
    )
    return {"status": "success"}

@app.get("/api/projects")
async def get_projects():
    return {
        "active_projects": list(project_registry.active_projects.keys()),
        "current_focus": project_registry.current_focus
    }

@app.post("/api/projects/switch/{project_id}")
async def switch_project(project_id: str):
    if project_id not in project_registry.active_projects:
        return {"error": "Project not loaded"}, 404
        
    old_focus = project_registry.current_focus
    if old_focus and old_focus != project_id and old_focus in project_registry.active_projects:
        old_ctx = project_registry.active_projects[old_focus]
        if old_ctx.sandbox.cmd_active:
            print(f"🛑 [REGISTRY] Killing active sandbox execution on {old_focus}")
            old_ctx.sandbox.cancel_active()
            
    if hasattr(orchestrator, 'cancel_current_task'):
        orchestrator.cancel_current_task()
        
    project_registry.switch_focus(project_id)
    ctx = project_registry.get_active()
    if ctx:
        await ws_manager._on_state_change(ctx.state.get_state(), ctx.state._state_version, time.time())
        
    return {"status": "success", "switched_to": project_id}

# -----------------
# SERVE REACT FRONTEND (STATIC)
# -----------------
frontend_build_path = os.path.join(os.path.dirname(__file__), "..", "dist")
if os.path.exists(frontend_build_path):
    app.mount("/", StaticFiles(directory=frontend_build_path, html=True), name="frontend")
else:
    print("⚠️ [SPARK] React build not found. Run 'npm run build' in root to serve HUD from backend.")

if __name__ == "__main__":
    print("🛸 [SPARK] Booting Sovereign Core...")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
