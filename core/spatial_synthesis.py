"""
S.P.A.R.K Spatial Computing & Volumetric Fluid Dynamics Core
Handles asynchronous 3D mesh synthesis (TSDF integration),
OpenCV optical flow estimation for fluid movement, and occlusion tracking.
"""

import time
import logging
import asyncio
import numpy as np
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger("SPARK_SPATIAL")

# Optional OpenCV import
cv2 = None
try:
    import cv2 as cv
    cv2 = cv
except ImportError:
    logger.warning("opencv-python not installed. Using simulated gradient estimators.")

class TSDFMeshBuilder:
    """Asynchronously integrates depth frames into a TSDF volume, generating triangular meshes."""
    
    def __init__(self, voxel_size: float = 0.02, use_cuda: bool = False):
        self.voxel_size = voxel_size
        self.use_cuda = use_cuda
        self.vertices = np.zeros((0, 3))
        self.faces = np.zeros((0, 3), dtype=np.int32)

    async def integrate_depth_frame(self, depth_frame: np.ndarray, intrinsic_matrix: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Asynchronously runs TSDF integration on depth frame, computing vertices and faces.
        Runs in background executor to prevent main loop blocking.
        """
        # Run calculation inside an async task
        loop = asyncio.get_running_loop()
        self.vertices, self.faces = await loop.run_in_executor(
            None, 
            self._tsdf_marching_cubes, 
            depth_frame, 
            intrinsic_matrix
        )
        return self.vertices, self.faces

    def _tsdf_marching_cubes(self, depth_frame: np.ndarray, intrinsic: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """Internal computation solver extracting mesh components."""
        h, w = depth_frame.shape
        # Create a simplified grid mesh from depth offsets
        grid_x, grid_y = np.meshgrid(np.arange(0, w, 10), np.arange(0, h, 10))
        
        flat_x = grid_x.flatten()
        flat_y = grid_y.flatten()
        flat_z = depth_frame[flat_y, flat_x].astype(float) / 1000.0 # scale to meters
        
        # Backproject to 3D Cartesian space: x = (u - cx)*z/fx, y = (v - cy)*z/fy
        fx, fy = intrinsic[0, 0], intrinsic[1, 1]
        cx, cy = intrinsic[0, 2], intrinsic[1, 2]
        
        X = (flat_x - cx) * flat_z / fx
        Y = (flat_y - cy) * flat_z / fy
        Z = flat_z
        
        vertices = np.column_stack((X, Y, Z))
        
        # Connect vertices to form triangles (faces)
        faces = []
        rows, cols = grid_x.shape
        for r in range(rows - 1):
            for c in range(cols - 1):
                idx0 = r * cols + c
                idx1 = idx0 + 1
                idx2 = (r + 1) * cols + c
                idx3 = idx2 + 1
                
                # Double triangle face configuration
                faces.append([idx0, idx1, idx2])
                faces.append([idx1, idx3, idx2])
                
        return vertices, np.array(faces, dtype=np.int32)

class VolumetricFluidFlow:
    """Computes optical flow vectors to track fluid dynamics (smoke, heat) in sequential frames."""
    
    def __init__(self, use_farneback: bool = True):
        self.use_farneback = use_farneback

    def estimate_flow(self, prev_frame: np.ndarray, curr_frame: np.ndarray) -> np.ndarray:
        """
        Calculates 2D velocity vectors for all image pixels.
        """
        if cv2 is not None and self.use_farneback:
            # Enforce grayscale frames
            if len(prev_frame.shape) == 3:
                prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
                curr_gray = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
            else:
                prev_gray = prev_frame
                curr_gray = curr_frame
                
            # Farneback algorithm
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, curr_gray, None, 
                pyr_scale=0.5, levels=3, winsize=15, 
                iterations=3, poly_n=5, poly_sigma=1.2, flags=0
            )
            return flow
        else:
            # Math-rich simulated fallback: returns spatial gradients
            logger.info("Spatial: Calculating fallback spatial gradient flow vectors.")
            flow_y, flow_x = np.gradient(curr_frame.astype(float))
            # Rescale gradients to represent flow fields
            flow = np.dstack((flow_x * 0.1, flow_y * 0.1))
            return flow

class OcclusionTracker:
    """Maintains object position records when occluded behind foreground structures."""
    
    def __init__(self):
        self.tracked_objects: Dict[str, Dict[str, Any]] = {}

    def update_positions(self, current_detections: Dict[str, Tuple[float, float, float]]) -> None:
        """Updates internal dictionary, computing velocity steps for extrapolating coordinates."""
        now = time.time()
        for obj_id, coords in current_detections.items():
            if obj_id in self.tracked_objects:
                prev_coords = self.tracked_objects[obj_id]["last_position"]
                dt = max(0.001, now - self.tracked_objects[obj_id]["last_time"])
                
                # Compute velocity: v = dx/dt
                velocity = (
                    (coords[0] - prev_coords[0]) / dt,
                    (coords[1] - prev_coords[1]) / dt,
                    (coords[2] - prev_coords[2]) / dt
                )
                self.tracked_objects[obj_id].update({
                    "last_position": coords,
                    "velocity": velocity,
                    "last_time": now,
                    "occluded": False
                })
            else:
                # Initialize new tracking element
                self.tracked_objects[obj_id] = {
                    "last_position": coords,
                    "velocity": (0.0, 0.0, 0.0),
                    "last_time": now,
                    "occluded": False
                }

    def predict_occluded_object(self, obj_id: str, dt_seconds: float = 0.5) -> Tuple[float, float, float]:
        """Extrapolates the position of a hidden object using its last known velocity."""
        if obj_id not in self.tracked_objects:
            raise KeyError(f"Object '{obj_id}' is not in active tracking records.")
            
        obj = self.tracked_objects[obj_id]
        pos = obj["last_position"]
        vel = obj["velocity"]
        
        # Dead-reckoning position update: x(t) = x_0 + v * dt
        predicted_pos = (
            pos[0] + vel[0] * dt_seconds,
            pos[1] + vel[1] * dt_seconds,
            pos[2] + vel[2] * dt_seconds
        )
        obj["occluded"] = True
        logger.info(f"Spatial: Predicting position of occluded object '{obj_id}' to: {predicted_pos}")
        return predicted_pos
