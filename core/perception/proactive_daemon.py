from __future__ import annotations

from typing import Any
import asyncio
import psutil

class ProactiveDaemon:
    def __init__(self, alert_callback: Any, cpu_limit: float = 95.0, ram_limit: float = 95.0):
        self.callback = alert_callback
        self.cpu_limit = cpu_limit
        self.ram_limit = ram_limit
        self.running = False
        self.monitor_task: asyncio.Task | None = None

    def start(self):
        self.running = True
        self.monitor_task = asyncio.create_task(self._monitor_loop())

    def stop(self):
        self.running = False
        if self.monitor_task:
            self.monitor_task.cancel()

    async def _monitor_loop(self):
        while self.running:
            try:
                await asyncio.sleep(5)
                cpu = psutil.cpu_percent()
                ram = psutil.virtual_memory().percent
                
                if cpu > self.cpu_limit:
                    await self.callback(f"[TELEMETRY_ALERT] CPU load is running critically high at {cpu}%.")
                if ram > self.ram_limit:
                    await self.callback(f"[TELEMETRY_ALERT] Memory usage is running critically high at {ram}%.")
            except asyncio.CancelledError:
                break
            except Exception:
                pass
