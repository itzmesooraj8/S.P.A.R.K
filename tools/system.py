from __future__ import annotations

from dataclasses import asdict, dataclass

import GPUtil
import psutil


@dataclass
class SystemStats:
    cpu_percent: float
    ram_used_gb: float
    ram_total_gb: float
    ram_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float
    gpu_name: str | None = None
    gpu_util_percent: float | None = None


def get_system_stats() -> dict:
    cpu = psutil.cpu_percent(interval=0.2)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    stats = SystemStats(
        cpu_percent=round(cpu, 1),
        ram_used_gb=round((memory.total - memory.available) / (1024 ** 3), 2),
        ram_total_gb=round(memory.total / (1024 ** 3), 2),
        ram_percent=round(memory.percent, 1),
        disk_used_gb=round((disk.total - disk.free) / (1024 ** 3), 2),
        disk_total_gb=round(disk.total / (1024 ** 3), 2),
        disk_percent=round(disk.percent, 1),
    )

    try:
        gpus = GPUtil.getGPUs()
        if gpus:
            stats.gpu_name = gpus[0].name
            stats.gpu_util_percent = round(gpus[0].load * 100, 1)
    except Exception:
        pass

    return asdict(stats)