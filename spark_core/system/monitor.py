import asyncio
import psutil
import time
from system.state import unified_state

class SystemMonitor:
    def __init__(self, interval: int = 5):
        self.interval = interval
        self.running = False
        print("⚙️ [SYSTEM] Background Monitor Initialized.")

    async def start_monitoring(self, ws_manager):
        self.running = True
        
        while self.running:
            # Poll metrics
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
            
            payload = {
                "cpu": cpu,
                "ram": ram,
                "disk": disk,
                "timestamp": int(time.time()),
            }
            
            # Use unified state dispatcher payload mutation instead of direct serialization
            unified_state.update("metrics", payload)

            # Example Event Rule Trigger (Simulated background intelligence)
            if cpu > 85.0:
                import json
                await ws_manager.broadcast(json.dumps({
                    "type": "WARNING", "msg": "CPU Spike Detected."
                }), "notifications")

            await asyncio.sleep(self.interval)

    def stop(self):
        self.running = False
