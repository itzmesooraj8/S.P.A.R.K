"""Sandbox fluid-flow monitor with optical-flow-backed anomaly detection."""

from __future__ import annotations

import logging
import re
import threading
import time
from pathlib import Path
from typing import Any, Optional

import numpy as np

from spatial.spatial_synthesis import SpatialSynthesisEngine

logger = logging.getLogger("SPARK_FLUID_FLOW_MONITOR")

_SUSPICIOUS_PATTERNS = (
    re.compile(r"\b(import\s+os|import\s+subprocess|os\.system\(|subprocess\.|eval\(|exec\(|__import__)", re.IGNORECASE),
    re.compile(r"\.\.[/\\]"),
)


def _broadcast_system_alert(payload: dict[str, Any]) -> None:
    try:
        from api.server import broadcast_system_alert

        broadcast_system_alert(payload)
    except Exception:
        pass


class FluidFlowMonitor:
    """Tracks sandbox file generation using local optical-flow and rate heuristics."""

    def __init__(self, sandbox_root: str | Path = "sandbox", scan_interval_seconds: float = 0.1, flow_engine: Optional[SpatialSynthesisEngine] = None) -> None:
        self.sandbox_root = Path(sandbox_root).expanduser().resolve()
        self.scan_interval_seconds = max(0.02, float(scan_interval_seconds))
        self.flow_engine = flow_engine or SpatialSynthesisEngine(voxel_size=0.02, grid_shape=(8, 8, 8))
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._previous_frame: Optional[np.ndarray] = None
        self._last_snapshot_time = time.time()
        self._last_file_count = 0
        self._last_total_bytes = 0
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def _validate_path(self, path: Path) -> Path:
        resolved = path.resolve()
        if resolved != self.sandbox_root and self.sandbox_root not in resolved.parents:
            raise PermissionError(f"Path '{resolved}' escapes the allowlisted sandbox root '{self.sandbox_root}'.")
        return resolved

    def _snapshot_files(self) -> list[Path]:
        files: list[Path] = []
        for candidate in self.sandbox_root.rglob("*"):
            if candidate.is_file():
                files.append(self._validate_path(candidate))
        return files

    def _build_density_frame(self, files: list[Path]) -> np.ndarray:
        frame = np.zeros((8, 8), dtype=np.float64)
        if not files:
            return frame
        sizes = [float(min(path.stat().st_size, 65535)) for path in files[:64]]
        for index, size in enumerate(sizes):
            row = index // 8
            col = index % 8
            frame[row, col] = size / 65535.0
        return frame

    def scan_once(self) -> dict[str, Any]:
        files = self._snapshot_files()
        now = time.time()
        elapsed = max(1e-3, now - self._last_snapshot_time)
        total_bytes = 0

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")[:8192]
            except Exception:
                content = ""
            total_bytes += len(content.encode("utf-8", errors="ignore"))
            if any(pattern.search(content) for pattern in _SUSPICIOUS_PATTERNS):
                message = f"Suspicious injection pattern detected in {file_path.name}"
                payload = {"source": "fluid_flow_monitor", "type": "sandbox_injection", "message": message, "severity": "critical"}
                _broadcast_system_alert(payload)
                raise PermissionError(message)

        current_frame = self._build_density_frame(files)
        if self._previous_frame is not None:
            try:
                self.flow_engine.estimate_flow(self._previous_frame, current_frame)
            except Exception as exc:
                logger.debug("Optical flow estimation skipped: %s", exc)
        self._previous_frame = current_frame

        generation_rate = max(0.0, len(files) - self._last_file_count) / elapsed
        byte_rate = max(0.0, total_bytes - self._last_total_bytes) / elapsed

        self._last_snapshot_time = now
        self._last_file_count = len(files)
        self._last_total_bytes = total_bytes

        if generation_rate > 64.0 or byte_rate > 1024 * 1024:
            message = f"Sandbox file generation rate exceeded safe bounds: files/sec={generation_rate:.2f}, bytes/sec={byte_rate:.2f}"
            payload = {"source": "fluid_flow_monitor", "type": "generation_rate_anomaly", "message": message, "severity": "warning"}
            _broadcast_system_alert(payload)
            raise PermissionError(message)

        return {
            "status": "ok",
            "file_count": len(files),
            "generation_rate_per_sec": generation_rate,
            "byte_rate_per_sec": byte_rate,
        }

    def start(self) -> None:
        if self._running:
            return
        self._running = True

        def _loop() -> None:
            while self._running:
                try:
                    self.scan_once()
                except PermissionError as exc:
                    logger.error("Fluid flow threat detected: %s", exc)
                    self._running = False
                    break
                except Exception as exc:
                    logger.debug("Fluid flow monitor loop error: %s", exc)
                time.sleep(self.scan_interval_seconds)

        self._thread = threading.Thread(target=_loop, daemon=True, name="spark-fluid-flow-monitor")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None
