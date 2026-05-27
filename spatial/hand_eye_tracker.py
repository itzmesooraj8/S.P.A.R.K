"""27-DoF skeletal tracking and gaze mapping for somatic interactions."""

from __future__ import annotations

import asyncio
import logging
import math
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

import numpy as np

logger = logging.getLogger("SPARK_SOMATIC_SKELETON")


@dataclass(slots=True)
class SkeletalFrame:
    joints_27dof: np.ndarray
    gesture: str
    gaze_xy: tuple[int, int]


class SomaticSkeletalTracker:
    """Maps multi-joint layouts into a 27-DoF skeletal encoding with gesture routing."""

    def __init__(self, squeeze_threshold: float = 0.08, toss_velocity_threshold: float = 1.5, screen_resolution: Tuple[int, int] = (1920, 1080)) -> None:
        self.squeeze_threshold = float(squeeze_threshold)
        self.toss_velocity_threshold = float(toss_velocity_threshold)
        self.screen_width, self.screen_height = screen_resolution
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self.cal_x = np.array([self.screen_width / 2.0, 1500.0, 0.0], dtype=np.float64)
        self.cal_y = np.array([self.screen_height / 2.0, 0.0, 1000.0], dtype=np.float64)

    @staticmethod
    def _finite(array: np.ndarray, label: str) -> np.ndarray:
        array = np.asarray(array, dtype=np.float64)
        if array.size == 0:
            raise ValueError(f"{label} cannot be empty.")
        if not np.all(np.isfinite(array)):
            raise FloatingPointError(f"{label} contains invalid numeric values.")
        return array

    def calculate_joint_angle(self, joint_base: np.ndarray, joint_mid: np.ndarray, joint_tip: np.ndarray) -> float:
        base = self._finite(joint_base, "joint_base")
        mid = self._finite(joint_mid, "joint_mid")
        tip = self._finite(joint_tip, "joint_tip")
        vector_u = mid - base
        vector_v = tip - mid
        norm_u = np.linalg.norm(vector_u)
        norm_v = np.linalg.norm(vector_v)
        if norm_u < 1e-6 or norm_v < 1e-6:
            return 0.0
        cosine = float(np.dot(vector_u, vector_v) / (norm_u * norm_v))
        cosine = max(-1.0, min(1.0, cosine))
        return float(np.arccos(cosine))

    def map_gaze_to_screen(self, pupil_center: Tuple[float, float], eye_canthus: Tuple[float, float]) -> Tuple[int, int]:
        dx = float(pupil_center[0]) - float(eye_canthus[0])
        dy = float(pupil_center[1]) - float(eye_canthus[1])
        x_screen = self.cal_x[0] + self.cal_x[1] * dx + self.cal_x[2] * dy
        y_screen = self.cal_y[0] + self.cal_y[1] * dx + self.cal_y[2] * dy
        return max(0, min(self.screen_width, int(x_screen))), max(0, min(self.screen_height, int(y_screen)))

    def _normalize_joints(self, joints: np.ndarray) -> np.ndarray:
        joints = self._finite(joints, "joints")
        joints = joints.reshape(-1, 3)
        if joints.shape[0] < 27:
            padding = np.zeros((27 - joints.shape[0], 3), dtype=np.float64)
            joints = np.vstack([joints, padding])
        return joints[:27]

    def encode_layout(self, joints: np.ndarray) -> np.ndarray:
        encoded = self._normalize_joints(joints).reshape(27, 3)
        norms = np.linalg.norm(encoded, axis=1, keepdims=True)
        encoded = np.divide(encoded, np.maximum(norms, 1e-6))
        if not np.all(np.isfinite(encoded)):
            raise FloatingPointError("Skeletal encoding produced invalid values.")
        return encoded

    def evaluate_gesture(self, landmarks: np.ndarray, prev_landmarks: Optional[np.ndarray] = None, dt: float = 0.033) -> str:
        landmarks = self._normalize_joints(landmarks)
        wrist = landmarks[0]
        fingertips = landmarks[[4, 8, 12, 16, 20]]
        mean_dist = float(np.mean(np.linalg.norm(fingertips - wrist, axis=1)))
        if mean_dist < self.squeeze_threshold:
            return "SQUEEZE"
        if prev_landmarks is not None:
            prev = self._normalize_joints(prev_landmarks)
            wrist_velocity = float(np.linalg.norm(wrist - prev[0]) / max(dt, 1e-6))
            if wrist_velocity > self.toss_velocity_threshold:
                return "TOSS"
            index_tip_delta = landmarks[8] - prev[8]
            if abs(index_tip_delta[0]) / max(dt, 1e-6) > 0.5 and abs(index_tip_delta[1]) / max(dt, 1e-6) < 0.2:
                return "SLIDE_LEFT" if index_tip_delta[0] < 0 else "SLIDE_RIGHT"
        return "NONE"

    def process_frame(self, joints: np.ndarray, prev_joints: Optional[np.ndarray] = None, pupil_center: Tuple[float, float] = (0.0, 0.0), eye_canthus: Tuple[float, float] = (0.0, 0.0)) -> SkeletalFrame:
        encoded = self.encode_layout(joints)
        gesture = self.evaluate_gesture(encoded, prev_joints)
        gaze = self.map_gaze_to_screen(pupil_center, eye_canthus)
        return SkeletalFrame(joints_27dof=encoded, gesture=gesture, gaze_xy=gaze)

    async def process_async(
        self,
        frame_source: Callable[[], np.ndarray],
        prev_frame: Optional[np.ndarray] = None,
        on_gesture: Optional[Callable[[str], None]] = None,
    ) -> SkeletalFrame:
        joints = frame_source()
        if asyncio.iscoroutine(joints):
            joints = await joints
        frame = self.process_frame(np.asarray(joints, dtype=np.float64), prev_frame)
        if frame.gesture != "NONE" and on_gesture:
            on_gesture(frame.gesture)
        return frame

    def start_stream(
        self,
        frame_source: Callable[[], np.ndarray],
        on_frame: Optional[Callable[[SkeletalFrame], None]] = None,
        on_gesture: Optional[Callable[[str], None]] = None,
        poll_interval_seconds: float = 1.0 / 30.0,
    ) -> None:
        if self._running:
            return
        self._running = True

        def _loop() -> None:
            prev = None
            while self._running:
                try:
                    joints = np.asarray(frame_source(), dtype=np.float64)
                    frame = self.process_frame(joints, prev)
                    prev = joints
                    if frame.gesture != "NONE" and on_gesture:
                        on_gesture(frame.gesture)
                    if on_frame:
                        on_frame(frame)
                except Exception as exc:
                    logger.error("Somatic skeletal monitor fault: %s", exc)
                    try:
                        from api.server import broadcast_system_alert

                        broadcast_system_alert({"source": "somatic_skeleton", "type": "tracking_error", "message": str(exc), "severity": "warning"})
                    except Exception:
                        pass
                threading.Event().wait(max(0.01, float(poll_interval_seconds)))

        self._thread = threading.Thread(target=_loop, daemon=True, name="spark-somatic-skeleton")
        self._thread.start()

    def stop_stream(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None


HandKinematicsTracker = SomaticSkeletalTracker
hand_tracker = SomaticSkeletalTracker()
PupilGazeAligner = SomaticSkeletalTracker
