from __future__ import annotations

import numpy as np

class ONNXObjectDetector:
    """Wrapper and tracking registry wrapper for ONNX local execution layers."""
    def __init__(self, onnx_model_path: str | None = None):
        self.model_path = onnx_model_path
        self.classes = {0: "person", 1: "hazard", 2: "component"}

    def detect_and_track(self, frame: np.ndarray) -> list[dict]:
        """Detect and persistently assign track IDs to spatial coordinates."""
        height, width, _ = frame.shape
        simulated_detections = []
        
        # Simulate tracking Person
        if height > 100:
            simulated_detections.append({
                "bbox": [50.0, 100.0, 80.0, 180.0],
                "confidence": 0.92,
                "label": "person",
                "track_id": 1
            })
            
        # Simulate tracking Component if frame fits target details
        if width > 300:
            simulated_detections.append({
                "bbox": [120.0, 200.0, 45.0, 45.0],
                "confidence": 0.88,
                "label": "component",
                "track_id": 2
            })
            
        return simulated_detections
