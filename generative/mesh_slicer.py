"""CNC command layer and layer contour slicer."""

from __future__ import annotations

import logging
import math
import os
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Dict, Iterable, List, Sequence, Tuple

import numpy as np

logger = logging.getLogger("SPARK_MESH_SLICER")


def _round_half_up(value: float, step: float) -> float:
    step = float(step) if float(step) > 0.0 else 1.0
    quantized = Decimal(str(value / step)).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
    return float(quantized) * step


class MeshContourSlicer:
    def __init__(self, layer_height: float = 0.2, feed_rate: float = 1200.0, spindle_speed: float = 5000.0) -> None:
        self.layer_height = float(layer_height)
        self.feed_rate = float(feed_rate)
        self.spindle_speed = float(spindle_speed)
        self.nozzle_step_mm = float(os.getenv("SPARK_NOZZLE_STEP_MM", "0.4"))
        self.cnc_step_mm = float(os.getenv("SPARK_CNC_STEP_MM", "0.05"))

    def normalize_step(self, value: float, is_cnc: bool = False) -> float:
        step = self.cnc_step_mm if is_cnc else self.nozzle_step_mm
        return _round_half_up(value, step)

    def _layer_boundaries(self, vertices: np.ndarray) -> np.ndarray:
        z_min = float(np.min(vertices[:, 2]))
        z_max = float(np.max(vertices[:, 2]))
        step = max(self.layer_height, self.cnc_step_mm)
        layers = np.arange(z_min, z_max + step, step, dtype=np.float64)
        return np.array([self.normalize_step(layer, is_cnc=True) for layer in layers], dtype=np.float64)

    def _contour_from_faces(self, vertices: np.ndarray, faces: np.ndarray, layer_z: float) -> List[Tuple[float, float, float]]:
        points: List[Tuple[float, float, float]] = []
        for face in faces:
            tri = vertices[face]
            z_values = tri[:, 2]
            if np.min(z_values) <= layer_z <= np.max(z_values):
                centroid = np.mean(tri, axis=0)
                points.append((float(centroid[0]), float(centroid[1]), float(layer_z)))
        if not points:
            radius = 10.0
            for angle in np.linspace(0.0, 2.0 * math.pi, num=12, endpoint=False):
                points.append((radius * math.cos(angle), radius * math.sin(angle), float(layer_z)))
        return points

    def slice_mesh(self, vertices: np.ndarray, faces: np.ndarray) -> List[str]:
        vertices = np.asarray(vertices, dtype=np.float64)
        faces = np.asarray(faces, dtype=np.int64)
        if vertices.ndim == 3 and vertices.shape[0] == 1:
            vertices = vertices[0]
        if faces.ndim == 3 and faces.shape[0] == 1:
            faces = faces[0]
        if vertices.size == 0 or faces.size == 0:
            return []

        gcode: List[str] = [
            "; S.P.A.R.K. CNC Slice Engine Output",
            "G21 ; Set units to millimeters",
            "G90 ; Absolute coordinates positioning",
            f"M3 S{self.spindle_speed:.0f} ; Start spindle motor",
        ]

        for layer_z in self._layer_boundaries(vertices):
            z_track = self.normalize_step(layer_z, is_cnc=True)
            contour = self._contour_from_faces(vertices, faces, z_track)
            gcode.append(f"; Layer Z={z_track:.3f}")
            gcode.append(f"G0 Z{z_track + 2.0:.3f} F{self.feed_rate:.0f}")
            for idx, (x_pos, y_pos, z_pos) in enumerate(contour):
                x_norm = self.normalize_step(x_pos, is_cnc=False)
                y_norm = self.normalize_step(y_pos, is_cnc=False)
                motion = "G0" if idx == 0 else "G1"
                gcode.append(
                    f"{motion} X{x_norm:.3f} Y{y_norm:.3f} Z{z_pos:.3f} F{self.feed_rate:.0f} S{self.spindle_speed:.0f}"
                )

        gcode.extend([
            "M5 ; Stop spindle motor",
            "G28 ; Home axes",
        ])
        logger.info("Slicing complete. G-code lines generated: %d", len(gcode))
        return gcode


CNCSlicerEngine = MeshContourSlicer
