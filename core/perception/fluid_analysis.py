from __future__ import annotations

import cv2
import numpy as np

class FluidSmokeAnalyzer:
    """Analyzes pixel displacement divergence using OpenCV Farneback Optical Flow."""
    def __init__(self):
        self.prev_gray = None

    def analyze_frame(self, frame: np.ndarray) -> dict[str, float]:
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self.prev_gray is None:
            self.prev_gray = gray
            return {"smoke_index": 0.0, "fluid_movement": 0.0}

        # Calculate optical flow field
        flow = cv2.calcOpticalFlowFarneback(
            self.prev_gray, gray, None, 0.5, 3, 15, 3, 5, 1.2, 0
        )
        self.prev_gray = gray

        vx = flow[..., 0]
        vy = flow[..., 1]
        
        # Spatial gradients
        dvx_dx = np.gradient(vx, axis=1)
        dvy_dy = np.gradient(vy, axis=0)
        divergence = dvx_dx + dvy_dy
        
        # Volumetric spreading score based on positive divergence thresholding
        fluid_movement = float(np.mean(np.abs(flow)))
        smoke_index = float(np.sum(divergence > 0.08) / divergence.size)

        return {
            "smoke_index": float(np.clip(smoke_index * 10, 0.0, 1.0)),
            "fluid_movement": float(np.clip(fluid_movement, 0.0, 50.0))
        }
