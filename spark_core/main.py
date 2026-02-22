import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os
import time

from ws.manager import ws_manager
from orchestrator.brain import AIOrchestrator
from system.monitor import SystemMonitor
from tools.sandbox import init_sandbox, teardown_sandbox
from intelligence.registry import project_registry

app = FastAPI(title="SPARK AI Core v2", version="2.0.0")

# CORS for local dev HUD
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Core Services
orchestrator = AIOrchestrator()
sys_monitor = SystemMonitor()

@app.on_event("startup")
async def startup_event():
    print("🛸 [SPARK] Core Node Initializing...")
    
    # Auto-Bootstrap Initial Project Domains
    workspace_root = os.path.dirname(os.path.dirname(__file__))
    frontend_root = os.path.join(workspace_root, "src")
    
    project_registry.load_project("spark_kernel", workspace_root)
    if os.path.exists(frontend_root):
        project_registry.load_project("spark_frontend", frontend_root)
        
    project_registry.switch_focus("spark_kernel")
    
    # Initialize the sandbox isolated execution environment for the legacy fallback/active focus
    await init_sandbox()
    # Start background intelligence loop
    asyncio.create_task(sys_monitor.start_monitoring(ws_manager))
    print("✅ [SPARK] Background monitor started.")

@app.on_event("shutdown")
async def shutdown_event():
    print("🛸 [SPARK] Core Node Shutting Down...")
    await teardown_sandbox()

# -----------------
# WEBSOCKET NAMESPACES
# -----------------
@app.websocket("/ws/ai")
async def websocket_ai(websocket: WebSocket):
    await ws_manager.connect(websocket, "ai")
    try:
        while True:
            raw_data = await websocket.receive_text()
            
            import json
            try:
                msg = json.loads(raw_data)
                if msg.get("type") == "CANCEL":
                    orchestrator.cancel_current_task()
                    continue
            except json.JSONDecodeError:
                # If it's pure text, treat as user message
                pass
            
            # Normal stream execution
            async def _run_stream():
                async for token in orchestrator.process_stream(raw_data):
                    await websocket.send_json({
                        "type": "TOKEN",
                        "content": token
                    })
            
            # Concurrency lock: Auto-kill previous stream if new user input overrides
            if orchestrator.current_task and not orchestrator.current_task.done():
                orchestrator.cancel_current_task()
                
            task = asyncio.create_task(_run_stream())
            orchestrator.current_task = task
            
            try:
                await task
            except asyncio.CancelledError:
                pass
            
            # Finalize Stream
            await websocket.send_json({
                "type": "DONE"
            })
            
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "ai")

@app.websocket("/ws/system")
async def websocket_system(websocket: WebSocket):
    await ws_manager.connect(websocket, "system")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, "system")

# -----------------
# API ENDPOINTS
# -----------------
class AuthRequest(BaseModel):
    username: str
    password: str

@app.post("/api/auth/login")
async def login(req: AuthRequest):
    from auth.jwt_handler import create_access_token
    # Placeholder simple auth for Phase 1
    if req.username == "root" and req.password == "sparkadmin":
        return {"access_token": create_access_token({"sub": req.username, "role": "ROOT"}), "type": "bearer"}
    return {"error": "Unauthorized"}

@app.get("/api/state")
async def get_state():
    return orchestrator.get_state()

# -----------------
# REGISTRY ENDPOINTS
# -----------------
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
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
