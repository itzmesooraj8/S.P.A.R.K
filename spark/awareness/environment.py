"""Environment Awareness — System and environment monitoring."""

from __future__ import annotations

import logging
import platform
import time
from typing import Any

logger = logging.getLogger("spark.awareness.environment")


class EnvironmentAwareness:
    """Monitors system environment (CPU, memory, network, etc.)."""

    def __init__(self) -> None:
        self._last_scan: float = 0.0
        self._system_info: dict[str, Any] = {}

    def scan(self) -> dict[str, Any]:
        info = {
            "platform": platform.system(),
            "hostname": platform.node(),
            "timestamp": time.time(),
        }
        try:
            import psutil
            info["cpu_percent"] = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            info["memory_percent"] = mem.percent
            info["memory_available_gb"] = round(mem.available / (1024**3), 2)
            net = psutil.net_io_counters()
            info["net_sent_mb"] = round(net.bytes_sent / (1024**2), 2)
            info["net_recv_mb"] = round(net.bytes_recv / (1024**2), 2)
        except ImportError:
            info["note"] = "psutil not available"
        self._system_info = info
        self._last_scan = time.time()
        return info

    def get_health(self) -> dict[str, Any]:
        info = self.scan()
        health = "healthy"
        if info.get("cpu_percent", 0) > 90:
            health = "critical"
        elif info.get("cpu_percent", 0) > 70:
            health = "warning"
        return {"status": health, **info}

    def is_network_available(self) -> bool:
        try:
            import requests
            r = requests.get("https://httpbin.org/get", timeout=3)
            return r.status_code == 200
        except Exception:
            return False
