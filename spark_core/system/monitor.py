import asyncio
import psutil
import time
import os
import hashlib
import json
try:
    import GPUtil
except ImportError:
    GPUtil = None

from system.state import unified_state
from intelligence.registry import project_registry
from intelligence.scanner import WorkspaceScanner
from intelligence.graph import CodeGraph
from intelligence.analyzer import run_flake8, run_mypy, run_bandit, run_complexity
from intelligence.pattern_memory import pattern_store
from ws.manager import ws_manager

class SystemMonitor:
    def __init__(self, interval: int = 2):
        self.interval = interval
        self.running = False
        print("⚙️ [SYSTEM] Background Hybrid Audit Monitor Initialized.")
        
        self.project_hashes = {}
        self.last_heavy_scan = {}
        self.heavy_scan_cooldown = {} # failures backoff

    def compute_project_hash(self, root_dir: str) -> str:
        mtimes = []
        for dirpath, _, filenames in os.walk(root_dir):
            if "node_modules" in dirpath or ".git" in dirpath or "site-packages" in dirpath or "__pycache__" in dirpath:
                continue
            for f in filenames:
                if f.endswith(".py"):
                    try:
                        mtimes.append(str(os.stat(os.path.join(dirpath, f)).st_mtime))
                    except Exception:
                        pass
        return hashlib.md5("".join(mtimes).encode()).hexdigest()

    async def run_fast_scan(self, pid: str, ctx):
        print(f"⚡ [AUDIT] Fast Scan triggered for {pid}")
        scanner = WorkspaceScanner(ctx.sandbox, CodeGraph())
        graph_data = await scanner.scan_workspace()
        
        if "error" not in graph_data:
            ctx.state.update("code_graph", graph_data)

    async def run_heavy_scan(self, pid: str, ctx):
        print(f"🛡️ [AUDIT] Heavy Scan triggered for {pid}")
        try:
            lint = await run_flake8(ctx.sandbox)
            types = await run_mypy(ctx.sandbox)
            vulns = await run_bandit(ctx.sandbox)
            cx = await run_complexity(ctx.sandbox)
            
            st = ctx.state.get_state()
            metrics = st.get("metrics", {})
            metrics["lint_errors"] = lint
            metrics["type_errors"] = types
            metrics["known_vulnerabilities"] = vulns
            metrics["complexity_score"] = cx
            ctx.state.update("metrics", metrics)
            
            self.last_heavy_scan[pid] = time.time()
            self.heavy_scan_cooldown[pid] = 0
            print(f"✅ [AUDIT] Heavy Scan complete for {pid} (Lint: {lint}, Types: {types})")
            return True
        except Exception as e:
            print(f"⚠️ [AUDIT] Heavy scan failed for {pid}: {e}")
            self.heavy_scan_cooldown[pid] = self.heavy_scan_cooldown.get(pid, 0) + 1
            return False

    def heavy_scan_needed(self, pid: str, ctx) -> bool:
        # Cooldown check
        if self.heavy_scan_cooldown.get(pid, 0) >= 3:
            # Backoff simple: wait til restarted
            return False
            
        last_scan = self.last_heavy_scan.get(pid, 0)
        if time.time() - last_scan > 120:
            return True
            
        # Or if trend is degrading
        trend = pattern_store.compute_trends(pid)
        if trend.get("risk_trend") == "DEGRADING":
            return True
            
        return False

    async def start_monitoring(self, ws_manager_instance):
        self.running = True
        
        last_net_io = psutil.net_io_counters() if hasattr(psutil, 'net_io_counters') else None
        last_net_time = time.time()
        
        while self.running:
            # Global CPU/RAM
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            # Battery
            battery = psutil.sensors_battery() if hasattr(psutil, 'sensors_battery') else None
            battery_pct = battery.percent if battery else 100
            charging = battery.power_plugged if battery else True
            
            # Network throughput mapped to 0-100% scale (rough approximation)
            network_pct = 0
            if last_net_io:
                current_time = time.time()
                current_net_io = psutil.net_io_counters()
                dt = current_time - last_net_time
                if dt > 0:
                    bytes_recv = current_net_io.bytes_recv - last_net_io.bytes_recv
                    bytes_sent = current_net_io.bytes_sent - last_net_io.bytes_sent
                    total_mbps = (bytes_recv + bytes_sent) * 8 / (1024 * 1024 * dt)
                    network_pct = min(100.0, total_mbps * 2) # Arbitrary scaling for HUD visualization
                last_net_io = current_net_io
                last_net_time = current_time
            
            # GPU
            gpu_pct = 0
            if GPUtil:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu_pct = gpus[0].load * 100
                except Exception:
                    pass
            else:
                gpu_pct = disk # fallback visualization if GPUtil not found

            payload = {
                "cpu": cpu,
                "ram": ram,
                "disk": disk,
                "gpu": gpu_pct,
                "network": network_pct,
                "battery": battery_pct,
                "charging": charging,
                "timestamp": int(time.time()),
            }
            unified_state.update("metrics", payload)
            
            # Hybrid Continuous Audit
            for pid, ctx in list(project_registry.active_projects.items()):
                current_hash = self.compute_project_hash(ctx.root_path)
                last_hash = self.project_hashes.get(pid)
                
                if current_hash != last_hash:
                    # File change detected!
                    self.project_hashes[pid] = current_hash
                    
                    await self.run_fast_scan(pid, ctx)
                    
                    if self.heavy_scan_needed(pid, ctx):
                        # Ensure only one heavy scan runs without blocking everything, but for safety await it
                        # with a pseudo-timeout
                        try:
                            await asyncio.wait_for(self.run_heavy_scan(pid, ctx), timeout=60.0)
                        except asyncio.TimeoutError:
                            print(f"⚠️ [AUDIT] Heavy scan timed out for {pid}")
                            self.heavy_scan_cooldown[pid] = self.heavy_scan_cooldown.get(pid, 0) + 1
                            
                    # Trigger analysis update so trend engine is refreshed
                    from intelligence.cross_analyzer import cross_analyzer
                    cross = cross_analyzer.analyze_all(project_registry)
                    
                    # Broadcast only on change
                    await ws_manager_instance.broadcast(json.dumps({
                        "type": "AUDIT_UPDATE",
                        "project": pid,
                        "health": cross.get("system_health_score")
                    }), "system")

            await asyncio.sleep(self.interval)

    def stop(self):
        self.running = False
