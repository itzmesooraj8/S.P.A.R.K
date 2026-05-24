from __future__ import annotations

from typing import Any
import numpy as np

class HandSkeletonTracker:
    """Evaluates Euclidean distances and angular deviations for MediaPipe 21 articulated hand joints."""
    def __init__(self):
        self.pinch_threshold = 0.04

    def parse_joints(self, joint_coords: np.ndarray) -> dict[str, Any]:
        if len(joint_coords) < 21:
            return {"gesture": "none", "pinch_distance": 0.0}

        # Thumb tip (4) and Index tip (8)
        thumb_tip = joint_coords[4]
        index_tip = joint_coords[8]
        
        dist = np.linalg.norm(thumb_tip - index_tip)
        gesture = "none"
        if dist < self.pinch_threshold:
            gesture = "pinch_select"

        return {
            "gesture": gesture,
            "pinch_distance": float(dist)
        }

class PhysicsHolographicController:
    """Physics-based holographic coordinate cursor tracking force, mass, and velocity."""
    def __init__(self):
        self.velocity = np.zeros(2)
        self.position = np.array([0.0, 0.0])
        self.mass = 1.0
        self.friction = 0.95

    def update_physics(self, force_vector: np.ndarray, dt: float = 1.0/60.0):
        # acceleration = Force / mass
        acc = force_vector / self.mass
        self.velocity = (self.velocity + acc * dt) * self.friction
        self.position = self.position + self.velocity * dt

    def get_eye_quadrant(self, pupil_center: tuple[float, float], socket_box: tuple[float, float, float, float]) -> int:
        # socket_box: (xmin, xmax, ymin, ymax)
        xmin, xmax, ymin, ymax = socket_box
        x, y = pupil_center
        
        u = (x - xmin) / (xmax - xmin + 1e-6)
        v = (y - ymin) / (ymax - ymin + 1e-6)
        
        if u >= 0.5:
            return 1 if v >= 0.5 else 4
        else:
            return 2 if v >= 0.5 else 3
