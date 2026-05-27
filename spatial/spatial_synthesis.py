"""TSDF integration, dense flow, and dead-reckoning spatial synthesis."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger("SPARK_SPATIAL_SYNTHESIS")

try:
    import cv2  # type: ignore
except Exception:  # pragma: no cover - optional dependency fallback
    cv2 = None


@dataclass(slots=True)
class TrackedSpatialObject:
    position: np.ndarray
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3, dtype=np.float64))
    last_update: float = field(default_factory=time.time)
    occluded: bool = False


class SpatialSynthesisEngine:
    """Processes depth, flow, and occlusion for spatial compute pipelines."""

    def __init__(self, voxel_size: float = 0.02, grid_shape: Tuple[int, int, int] = (64, 64, 64)) -> None:
        self.voxel_size = float(voxel_size)
        self.grid_shape = tuple(int(v) for v in grid_shape)
        self.tsdf = np.ones(self.grid_shape, dtype=np.float64)
        self.weights = np.zeros(self.grid_shape, dtype=np.float64)
        self._lock = threading.RLock()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.objects: Dict[str, TrackedSpatialObject] = {}

    @staticmethod
    def _finite(array: np.ndarray, label: str) -> np.ndarray:
        array = np.asarray(array, dtype=np.float64)
        if array.size == 0:
            raise ValueError(f"{label} cannot be empty.")
        if not np.all(np.isfinite(array)):
            raise FloatingPointError(f"{label} contains invalid numeric values.")
        return array

    def integrate_tsdf(self, depth_frame: np.ndarray, intrinsic_matrix: np.ndarray) -> np.ndarray:
        depth = self._finite(depth_frame, "depth_frame")
        intrinsic = self._finite(intrinsic_matrix, "intrinsic_matrix")
        if depth.ndim != 2:
            raise ValueError("Depth frame must be 2D.")
        if intrinsic.shape != (3, 3):
            raise ValueError("Intrinsic matrix must be 3x3.")

        height, width = depth.shape
        grid_y, grid_x = np.indices(self.grid_shape[:2])
        sample_y = np.clip((grid_y * height / self.grid_shape[0]).astype(int), 0, height - 1)
        sample_x = np.clip((grid_x * width / self.grid_shape[1]).astype(int), 0, width - 1)
        sampled_depth = depth[sample_y, sample_x] / 1000.0
        fx, fy = intrinsic[0, 0], intrinsic[1, 1]
        cx, cy = intrinsic[0, 2], intrinsic[1, 2]
        z_axis = np.linspace(0.0, 1.0, self.grid_shape[2], dtype=np.float64)

        with self._lock:
            for z_index, z_value in enumerate(z_axis):
                sdf_slice = sampled_depth - z_value
                truncated = np.clip(sdf_slice / max(self.voxel_size, 1e-6), -1.0, 1.0)
                self.tsdf[:, :, z_index] = 0.9 * self.tsdf[:, :, z_index] + 0.1 * truncated
                self.weights[:, :, z_index] += 1.0
        return self.tsdf.copy()

    def marching_cubes_mesh(self, threshold: float = 0.0) -> Tuple[np.ndarray, np.ndarray]:
        with self._lock:
            occupancy = self.tsdf <= threshold
        vertices = []
        faces = []
        step = self.voxel_size
        for z in range(occupancy.shape[2] - 1):
            for y in range(occupancy.shape[0] - 1):
                for x in range(occupancy.shape[1] - 1):
                    cube = occupancy[y : y + 2, x : x + 2, z : z + 2]
                    if not cube.any() or cube.all():
                        continue
                    base = len(vertices)
                    cube_vertices = np.array(
                        [
                            [x, y, z],
                            [x + 1, y, z],
                            [x + 1, y + 1, z],
                            [x, y + 1, z],
                            [x, y, z + 1],
                            [x + 1, y, z + 1],
                            [x + 1, y + 1, z + 1],
                            [x, y + 1, z + 1],
                        ],
                        dtype=np.float64,
                    ) * step
                    vertices.extend(cube_vertices.tolist())
                    faces.extend(
                        [
                            [base, base + 1, base + 2],
                            [base, base + 2, base + 3],
                            [base + 4, base + 5, base + 6],
                            [base + 4, base + 6, base + 7],
                        ]
                    )
        return np.asarray(vertices, dtype=np.float64), np.asarray(faces, dtype=np.int64)

    def estimate_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> np.ndarray:
        prev = self._finite(prev_frame, "prev_frame")
        curr = self._finite(curr_frame, "curr_frame")
        if cv2 is not None and prev.ndim >= 2 and curr.ndim >= 2:
            prev_gray = cv2.cvtColor(prev, cv2.COLOR_BGR2GRAY) if prev.ndim == 3 else prev
            curr_gray = cv2.cvtColor(curr, cv2.COLOR_BGR2GRAY) if curr.ndim == 3 else curr
            return cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        grad_y, grad_x = np.gradient(curr.astype(np.float64))
        return np.dstack((grad_x * 0.1, grad_y * 0.1))

    def update_position(self, object_id: str, position: Tuple[float, float, float]) -> None:
        now = time.time()
        pos = np.asarray(position, dtype=np.float64)
        if object_id in self.objects:
            tracked = self.objects[object_id]
            dt = max(1e-3, now - tracked.last_update)
            tracked.velocity = (pos - tracked.position) / dt
            tracked.position = pos
            tracked.last_update = now
            tracked.occluded = False
        else:
            self.objects[object_id] = TrackedSpatialObject(position=pos)

    def predict_occluded(self, object_id: str, dt_seconds: float = 0.5) -> Tuple[float, float, float]:
        if object_id not in self.objects:
            raise KeyError(f"Object '{object_id}' is not in active tracking records.")
        tracked = self.objects[object_id]
        tracked.occluded = True
        predicted = tracked.position + tracked.velocity * float(dt_seconds)
        return tuple(float(v) for v in predicted)

    def start_dead_reckoning(self, update_source: Callable[[], Dict[str, Tuple[float, float, float]]], poll_interval_seconds: float = 0.05) -> None:
        if self._running:
            return
        self._running = True

        def _loop() -> None:
            while self._running:
                try:
                    for object_id, position in update_source().items():
                        self.update_position(object_id, position)
                except Exception as exc:
                    logger.error("Spatial dead-reckoning fault: %s", exc)
                    try:
                        from api.server import broadcast_system_alert

                        broadcast_system_alert({"source": "spatial_synthesis", "type": "dead_reckoning_error", "message": str(exc), "severity": "warning"})
                    except Exception:
                        pass
                time.sleep(max(0.01, float(poll_interval_seconds)))

        self._thread = threading.Thread(target=_loop, daemon=True, name="spark-spatial-synthesis")
        self._thread.start()

    def stop_dead_reckoning(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None


class TSDFMeshBuilder(SpatialSynthesisEngine):
    async def integrate_depth_frame(self, depth_frame: np.ndarray, intrinsic_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.integrate_tsdf, depth_frame, intrinsic_matrix)
        return self.marching_cubes_mesh()


class VolumetricFluidFlow(SpatialSynthesisEngine):
    def __init__(self, use_farneback: bool = True):
        super().__init__()
        self.use_farneback = use_farneback


class OcclusionTracker(SpatialSynthesisEngine):
    def update_positions(self, current_detections: Dict[str, Tuple[float, float, float]]) -> None:
        for object_id, position in current_detections.items():
            self.update_position(object_id, position)

    def predict_occluded_object(self, obj_id: str, dt_seconds: float = 0.5) -> Tuple[float, float, float]:
        return self.predict_occluded(obj_id, dt_seconds)
