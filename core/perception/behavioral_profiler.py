from __future__ import annotations

import numpy as np

class BehavioralProfiler:
    """Calculates postural balance gait variances and facial muscle offsets using landmarks."""
    def __init__(self):
        self.prev_postures = []

    def evaluate_pose(self, face_landmarks: np.ndarray, body_skeleton: np.ndarray) -> dict[str, float]:
        # Micro-expression: relative brow distance displacement
        if len(face_landmarks) > 110:
            brow_dist = np.linalg.norm(face_landmarks[70] - face_landmarks[107])
            expression_score = float(np.clip(brow_dist * 5.0, 0.0, 1.0))
        else:
            expression_score = 0.0

        # Gait postural imbalance: mid-shoulder to mid-hip vertical alignment deviation
        if len(body_skeleton) > 24:
            shoulder_mid = (body_skeleton[11] + body_skeleton[12]) / 2.0
            hip_mid = (body_skeleton[23] + body_skeleton[24]) / 2.0
            balance_vector = shoulder_mid - hip_mid
            gait_imbalance = float(np.abs(balance_vector[0])) # lateral lean offset
        else:
            gait_imbalance = 0.0

        return {
            "micro_expression_stress": expression_score,
            "gait_imbalance": float(np.clip(gait_imbalance, 0.0, 1.0))
        }
