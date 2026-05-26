"""
S.P.A.R.K Articulated Interface Geometry & Eye Tracking Core
Computes 27-DoF hand skeletal landmark vector angles, interprets interaction gestures,
and tracks human pupil gaze vectors relative to screen dimensions.
"""

import numpy as np
import logging
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger("SPARK_INTERACTION")

class HandKinematicsTracker:
    """Computes relative angles of 27-DoF hand joint skeletons and flags interaction gestures."""
    
    def __init__(self, squeeze_threshold: float = 0.08, toss_velocity_threshold: float = 1.5):
        self.squeeze_threshold = squeeze_threshold
        self.toss_velocity_threshold = toss_velocity_threshold

    def calculate_joint_angle(self, joint_base: np.ndarray, joint_mid: np.ndarray, joint_tip: np.ndarray) -> float:
        """
        Calculates relative angle (theta) in radians between adjacent bone segments.
        Using: theta = acos( (u . v) / (||u|| * ||v||) )
        """
        vector_u = joint_mid - joint_base
        vector_v = joint_tip - joint_mid
        
        norm_u = np.linalg.norm(vector_u)
        norm_v = np.linalg.norm(vector_v)
        
        if norm_u < 1e-6 or norm_v < 1e-6:
            return 0.0
            
        dot_product = np.dot(vector_u, vector_v)
        cos_theta = dot_product / (norm_u * norm_v)
        
        # Clean numerical bounds
        cos_theta = max(-1.0, min(1.0, cos_theta))
        return float(np.arccos(cos_theta))

    def evaluate_gesture(self, landmarks: np.ndarray, prev_landmarks: Optional[np.ndarray] = None, dt: float = 0.033) -> str:
        """
        Interprets gestures (squeeze, slide, toss) based on landmark distances and velocities.
        landmarks: array of shape (21, 3) representing 21 hand joints.
        """
        # Landmark 0: Wrist. Landmarks 4, 8, 12, 16, 20: Fingertips.
        wrist = landmarks[0]
        fingertips = landmarks[[4, 8, 12, 16, 20]]
        
        # Calculate mean distance from fingertips to wrist
        dists = np.linalg.norm(fingertips - wrist, axis=1)
        mean_dist = np.mean(dists)
        
        # 1. Squeeze detection (fingertips compressed close to wrist)
        if mean_dist < self.squeeze_threshold:
            return "SQUEEZE"
            
        # 2. Velocity-based Toss detection
        if prev_landmarks is not None:
            wrist_prev = prev_landmarks[0]
            velocity = np.linalg.norm(wrist - wrist_prev) / dt
            if velocity > self.toss_velocity_threshold:
                return "TOSS"
                
            # 3. Slide detection (index finger tip horizontal translation)
            index_tip = landmarks[8]
            index_tip_prev = prev_landmarks[8]
            horizontal_disp = index_tip[0] - index_tip_prev[0]
            vertical_disp = abs(index_tip[1] - index_tip_prev[1])
            
            if abs(horizontal_disp) / dt > 0.5 and vertical_disp / dt < 0.2:
                return "SLIDE_LEFT" if horizontal_disp < 0 else "SLIDE_RIGHT"
                
        return "NONE"

class PupilGazeAligner:
    """Calculates screen coordinate gaze points from pupil center displacement vectors."""
    
    def __init__(self, screen_resolution: Tuple[int, int] = (1920, 1080)):
        self.screen_width, self.screen_height = screen_resolution
        
        # Calibration polynomial coefficients: X_screen = c_0 + c_1*dx + c_2*dy
        self.cal_x = np.array([960.0, 1500.0, 0.0]) # Default horizontal coefficients
        self.cal_y = np.array([540.0, 0.0, 1000.0]) # Default vertical coefficients

    def map_gaze_to_screen(self, pupil_center: Tuple[float, float], eye_canthus: Tuple[float, float]) -> Tuple[int, int]:
        """Maps pupil displacement vector relative to the eye corner to screen pixels."""
        # Calculate displacement vector (dx, dy)
        dx = pupil_center[0] - eye_canthus[0]
        dy = pupil_center[1] - eye_canthus[1]
        
        # Map using calibration coefficients
        x_screen = self.cal_x[0] + self.cal_x[1] * dx + self.cal_x[2] * dy
        y_screen = self.cal_y[0] + self.cal_y[1] * dx + self.cal_y[2] * dy
        
        # Clip coordinates within screen boundaries
        x_clamped = max(0, min(self.screen_width, int(x_screen)))
        y_clamped = max(0, min(self.screen_height, int(y_screen)))
        
        return x_clamped, y_clamped
