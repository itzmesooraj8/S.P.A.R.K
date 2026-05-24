from __future__ import annotations

import numpy as np

class OcclusionTracker:
    """Maintains active coordinates history and predicts coordinates when targets are occluded."""
    def __init__(self):
        # Bounding box maps: ID -> {coords: [x,y,z], velocity: [vx,vy,vz], occluded: bool, frames_lost: int}
        self.registry = {}

    def update(self, detected_objects: dict[int, np.ndarray]):
        active_ids = set(detected_objects.keys())
        
        # Update active trackers
        for obj_id, target in detected_objects.items():
            if obj_id in self.registry:
                prev = self.registry[obj_id]["coords"]
                dt = 1.0 / 30.0  # 30 FPS target
                velocity = (target - prev) / dt
                self.registry[obj_id] = {
                    "coords": target,
                    "velocity": velocity,
                    "occluded": False,
                    "frames_lost": 0
                }
            else:
                self.registry[obj_id] = {
                    "coords": target,
                    "velocity": np.zeros_like(target),
                    "occluded": False,
                    "frames_lost": 0
                }

        # Extrapolate for occluded trackers
        for obj_id in list(self.registry.keys()):
            if obj_id not in active_ids:
                data = self.registry[obj_id]
                data["frames_lost"] += 1
                if data["frames_lost"] < 90:  # 3 seconds persistence
                    data["occluded"] = True
                    dt = 1.0 / 30.0
                    # Newtonian linear prediction
                    data["coords"] = data["coords"] + data["velocity"] * dt
                else:
                    # Clean up long lost targets
                    del self.registry[obj_id]

    def get_object_position(self, obj_id: int) -> tuple[np.ndarray, bool]:
        if obj_id in self.registry:
            return self.registry[obj_id]["coords"], self.registry[obj_id]["occluded"]
        return np.zeros(3), False
