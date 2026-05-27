"""Voxel topology generation and structural compliance optimization."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Tuple

import numpy as np

logger = logging.getLogger("SPARK_GENERATIVE_CAD")


@dataclass(slots=True)
class MeshEvaluationResult:
    max_stress_mpa: float
    yield_strength_mpa: float
    passed: bool
    weak_spots_count: int
    weak_spot_elements: list[int]


class VoxelTopologyEngine:
    """SIMP-based voxel topology optimizer with lightweight FEA validation hooks."""

    def __init__(
        self,
        nelx: int = 24,
        nely: int = 12,
        nelz: int = 8,
        volume_fraction: float = 0.45,
        volfrac: float | None = None,
        penal: float = 3.0,
        e_min: float = 1.0e-9,
        e_0: float = 1.0,
        yield_strength_mpa: float = 250.0,
    ) -> None:
        self.nelx = max(1, int(nelx))
        self.nely = max(1, int(nely))
        self.nelz = max(1, int(nelz))
        if volfrac is not None:
            volume_fraction = volfrac
        self.volume_fraction = float(np.clip(volume_fraction, 0.01, 1.0))
        self.penal = float(penal)
        self.e_min = float(e_min)
        self.e_0 = float(e_0)
        self.yield_strength_mpa = float(yield_strength_mpa)

    @staticmethod
    def _finite_or_default(value: float, default: float) -> float:
        numeric = float(value)
        return numeric if np.isfinite(numeric) else default

    def initialize_density(self) -> np.ndarray:
        return np.full((self.nelz, self.nely, self.nelx), self.volume_fraction, dtype=np.float64)

    def compliance_proxy(self, density: np.ndarray) -> float:
        penalty = np.power(np.clip(density, 0.0, 1.0), self.penal)
        stiffness = self.e_min + penalty * (self.e_0 - self.e_min)
        load_field = 1.0 + self._synthetic_load_field(density.shape)
        return float(np.sum(load_field / np.maximum(stiffness, self.e_min)))

    def _synthetic_load_field(self, shape: Tuple[int, int, int]) -> np.ndarray:
        z, y, x = np.indices(shape)
        center = np.array([(shape[0] - 1) / 2.0, (shape[1] - 1) / 2.0, shape[2] - 1], dtype=np.float64)
        distance = np.sqrt((z - center[0]) ** 2 + (y - center[1]) ** 2 + (x - center[2]) ** 2)
        return 1.0 / (1.0 + distance)

    def optimize(self, iterations: int = 8, target_volume_fraction: float | None = None) -> np.ndarray:
        """Return a density matrix optimized with a compact SIMP update loop."""
        target = self.volume_fraction if target_volume_fraction is None else float(np.clip(target_volume_fraction, 0.01, 1.0))
        density = self.initialize_density()
        sensitivity = self._synthetic_load_field(density.shape)

        for _ in range(max(1, int(iterations))):
            stiffness = self.e_min + np.power(np.clip(density, 0.0, 1.0), self.penal) * (self.e_0 - self.e_min)
            compliance = self.compliance_proxy(density)
            dc = -self.penal * np.power(np.maximum(density, 1e-6), self.penal - 1.0) * sensitivity * (1.0 + compliance * 1e-6)

            lower, upper = 0.0, 1.0e5
            updated = np.empty_like(density)
            for _inner in range(30):
                mid = 0.5 * (lower + upper)
                ratio = np.sqrt(np.maximum(0.0, -dc / np.maximum(mid, 1e-12)))
                candidate = np.clip(density * ratio, density - 0.2, density + 0.2)
                updated[:] = np.clip(candidate, 0.01, 1.0)
                mean_volume = float(np.mean(updated))
                if mean_volume > target:
                    lower = mid
                else:
                    upper = mid
                if abs(mean_volume - target) < 1e-4:
                    break
            density = updated.copy()

        if not np.all(np.isfinite(density)):
            raise FloatingPointError("Density matrix contains invalid numeric values.")
        logger.info("Voxel SIMP optimization completed with shape %s", density.shape)
        return density

    def evaluate_mesh(
        self,
        vertices: np.ndarray,
        faces: np.ndarray,
        force_vector: Tuple[float, float, float] = (0.0, 0.0, 1.0),
    ) -> Dict[str, Any]:
        """Approximate von Mises stress and flag elements crossing the yield threshold."""
        vertices = np.asarray(vertices, dtype=np.float64)
        faces = np.asarray(faces, dtype=np.int64)
        if vertices.size == 0 or faces.size == 0:
            return {
                "max_stress_mpa": 0.0,
                "yield_strength_mpa": self.yield_strength_mpa,
                "passed": True,
                "weak_spots_count": 0,
                "weak_spot_elements": [],
            }

        force = np.asarray(force_vector, dtype=np.float64)
        force_mag = float(np.linalg.norm(force))
        centroids = np.array([np.mean(vertices[face], axis=0) for face in faces], dtype=np.float64)
        lever_arm = np.maximum(0.1, np.abs(centroids[:, 2]))
        projected = force_mag * lever_arm / (1.0 + np.abs(centroids[:, 0]) + np.abs(centroids[:, 1]))
        shape_factor = 1.0 + np.linalg.norm(centroids, axis=1)
        stress_field = projected * shape_factor

        weak_spots = np.where(stress_field > self.yield_strength_mpa)[0].tolist()
        max_stress = float(np.max(stress_field)) if len(stress_field) else 0.0
        return {
            "max_stress_mpa": max_stress,
            "yield_strength_mpa": self.yield_strength_mpa,
            "passed": bool(max_stress < self.yield_strength_mpa),
            "weak_spots_count": len(weak_spots),
            "weak_spot_elements": weak_spots,
        }

    def solve(self, iterations: int = 8, target_volume_fraction: float | None = None) -> Dict[str, Any]:
        density = self.optimize(iterations=iterations, target_volume_fraction=target_volume_fraction)
        return {
            "density_matrix": density,
            "average_density": float(np.mean(density)),
            "compliance_proxy": self.compliance_proxy(density),
            "volume_fraction": float(np.mean(density)),
        }


class CADFEAValidator:
    def __init__(self, yield_strength_mpa: float = 250.0):
        self.yield_strength_mpa = float(yield_strength_mpa)

    def validate_mesh(self, vertices: np.ndarray, faces: np.ndarray, force_vector: Tuple[float, float, float]) -> Dict[str, Any]:
        engine = VoxelTopologyEngine(yield_strength_mpa=self.yield_strength_mpa)
        return engine.evaluate_mesh(vertices, faces, force_vector)


class ToleranceCalibrator:
    def __init__(self, nozzle_diameter: float = 0.4, cnc_tolerance: float = 0.05):
        self.nozzle_diameter = float(nozzle_diameter)
        self.cnc_tolerance = float(cnc_tolerance)

    def adjust_clearance(self, nominal_width: float, is_cnc: bool = False) -> float:
        resolution = self.cnc_tolerance if is_cnc else self.nozzle_diameter
        steps = int((float(nominal_width) / resolution) + 0.5)
        adjusted = max(resolution, steps * resolution)
        return float(adjusted)


SIMPOptimizer2D = VoxelTopologyEngine
