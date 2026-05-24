from __future__ import annotations

import numpy as np

class BallisticTrajectoryPredictor:
    """Predicts intercept and trajectory maps using Newtonian vector kinematics."""
    def __init__(self, g: float = -9.81):
        self.g_vec = np.array([0.0, g, 0.0])
        self.history = {} # track_id -> list of (timestamp, coords)

    def register_position(self, track_id: int, coords: np.ndarray, timestamp: float):
        if track_id not in self.history:
            self.history[track_id] = []
        self.history[track_id].append((timestamp, coords))
        if len(self.history[track_id]) > 10:
            self.history[track_id].pop(0)

    def predict_intercept(self, track_id: int, time_horizon: float) -> np.ndarray:
        history = self.history.get(track_id, [])
        if len(history) < 3:
            return np.zeros(3) if not history else history[-1][1]

        t0, x0 = history[-1]
        t1, x1 = history[-2]
        t2, x2 = history[-3]

        dt1 = t0 - t1
        dt2 = t1 - t2
        if dt1 == 0 or dt2 == 0:
            return x0

        # Average velocities
        v0 = (x0 - x1) / dt1
        v1 = (x1 - x2) / dt2
        
        # Finite difference acceleration
        a = (v0 - v1) / dt1

        # Intercept equation: x(t) = x0 + v0*dt + 0.5 * (a + g) * dt^2
        future_x = x0 + v0 * time_horizon + 0.5 * (a + self.g_vec) * (time_horizon ** 2)
        return future_x
