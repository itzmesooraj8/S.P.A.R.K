from __future__ import annotations

import cv2
import numpy as np

class NetworkSensorStitcher:
    """Homography transformation engine that stitches multi-camera visual feeds onto one master coordinate plane."""
    def __init__(self):
        self.homography_matrices = {}

    def register_node(self, node_id: int, src_pts: np.ndarray, dst_pts: np.ndarray):
        H, _ = cv2.findHomography(src_pts, dst_pts)
        self.homography_matrices[node_id] = H

    def warp_and_stitch(self, frames_dict: dict[int, np.ndarray], output_shape: tuple[int, int]) -> np.ndarray:
        canvas = np.zeros((output_shape[0], output_shape[1], 3), dtype=np.uint8)
        
        for node_id, frame in frames_dict.items():
            if node_id in self.homography_matrices:
                warped = cv2.warpPerspective(
                    frame, self.homography_matrices[node_id], (output_shape[1], output_shape[0])
                )
                mask = warped > 0
                canvas[mask] = warped[mask]
            else:
                # Default overlay at coordinate origin
                h, w = frame.shape[:2]
                canvas[0:min(h, output_shape[0]), 0:min(w, output_shape[1])] = frame[0:min(h, output_shape[0]), 0:min(w, output_shape[1])]
                
        return canvas

class MultiSpectralLayerer:
    """Real-time overlays of Thermal IR hot vectors onto RGB frames combined with de-noising filters."""
    def fuse_spectral_feeds(self, rgb_frame: np.ndarray, thermal_frame: np.ndarray) -> np.ndarray:
        if rgb_frame.shape[:2] != thermal_frame.shape[:2]:
            thermal_resized = cv2.resize(thermal_frame, (rgb_frame.shape[1], rgb_frame.shape[0]))
        else:
            thermal_resized = thermal_frame

        thermal_gray = cv2.cvtColor(thermal_resized, cv2.COLOR_BGR2GRAY) if len(thermal_resized.shape) == 3 else thermal_resized
        # Mask high-temperature pixels (threshold 180)
        _, hot_mask = cv2.threshold(thermal_gray, 180, 255, cv2.THRESH_BINARY)
        
        fused = rgb_frame.copy()
        heat_color = cv2.applyColorMap(thermal_gray, cv2.COLORMAP_JET)
        
        # Blend heat signature over standard frame
        mask_indices = hot_mask > 0
        fused[mask_indices] = cv2.addWeighted(
            fused[mask_indices], 0.3, heat_color[mask_indices], 0.7, 0
        )
        
        # Apply NLMeans de-noising to final frame with fallback for restricted environments
        try:
            denoised = cv2.fastNlMeansDenoisingColored(fused, None, 10, 10, 7, 21)
            return denoised
        except Exception:
            try:
                return cv2.bilateralFilter(fused, 5, 75, 75)
            except Exception:
                return fused
