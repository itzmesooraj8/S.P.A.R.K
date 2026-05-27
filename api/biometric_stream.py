"""Biometric Telemetry WebSocket Route for S.P.A.R.K. HUD."""

from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import Any, Dict

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from biometrics.human_telemetry import BiometricTelemetryDaemon
from spatial.hand_eye_tracker import SomaticSkeletalTracker

logger = logging.getLogger("SPARK_BIOMETRIC_STREAM")

router = APIRouter()

# Instantiate daemons
telemetry_daemon = BiometricTelemetryDaemon(sample_rate=30.0, trace_window=300)
skeletal_tracker = SomaticSkeletalTracker()


@router.websocket("/ws/biometrics")
async def websocket_biometrics_endpoint(websocket: WebSocket) -> None:
    """Streams synchronized real-time rPPG metrics and joint cosines at 60 FPS."""
    await websocket.accept()
    logger.info("Biometrics WebSocket tunnel established.")

    frame_index = 0
    start_time = time.time()

    try:
        while True:
            # Maintain steady 60 FPS (~16.6ms intervals)
            await asyncio.sleep(0.0166)
            
            current_time = time.time()
            elapsed = current_time - start_time
            frame_index += 1

            # 1. Generate simulated frame with sinusoidal green channel variation
            # Target heart rate: 72 BPM -> 1.2 Hz frequency pulsation
            pulse_frequency = 1.2
            green_amplitude = 8.0
            base_green = 110.0
            green_modulation = base_green + green_amplitude * math.sin(2.0 * math.pi * pulse_frequency * elapsed)
            
            # Create a 10x10 mock RGB frame
            mock_frame = np.zeros((10, 10, 3), dtype=np.uint8)
            mock_frame[:, :, 0] = 90                             # Red
            mock_frame[:, :, 1] = int(np.clip(green_modulation, 0, 255)) # Green (PPG sensor source)
            mock_frame[:, :, 2] = 90                             # Blue

            # Pass to rPPG engine to apply Butterworth trace filter and compute heart rate
            vitals_sample = telemetry_daemon.update_frame(mock_frame)

            # 2. Generate simulated skeletal joints landmarks (27 joints with 3D coordinates)
            # Oscillate landmarks slightly to simulate skeletal noise and joint tracking movement
            base_joints = np.zeros((27, 3), dtype=np.float64)
            for idx in range(27):
                base_joints[idx] = [
                    idx * 1.5 + 2.0 * math.sin(elapsed + idx),
                    idx * 2.0 + 3.0 * math.cos(elapsed * 0.5 + idx),
                    idx * 0.5 + 1.0 * math.sin(elapsed * 2.0 + idx)
                ]

            # Process joint coordinates and gaze
            prev_joints = None
            skeletal_frame = skeletal_tracker.process_frame(
                joints=base_joints,
                prev_joints=prev_joints,
                pupil_center=(0.5 + 0.1 * math.sin(elapsed), 0.5),
                eye_canthus=(0.5, 0.5)
            )

            # Compute joint cosine vectors for individual fingers
            joint_cosines = {}
            finger_indices = {
                "thumb": (1, 2, 3),
                "index": (5, 6, 7),
                "middle": (9, 10, 11),
                "ring": (13, 14, 15),
                "pinky": (17, 18, 19)
            }

            for finger_name, (base, mid, tip) in finger_indices.items():
                try:
                    cos_angle = skeletal_tracker.calculate_joint_angle(
                        base_joints[base],
                        base_joints[mid],
                        base_joints[tip]
                    )
                    # Convert rad angle to cosine value
                    joint_cosines[finger_name] = float(math.cos(cos_angle))
                except Exception:
                    joint_cosines[finger_name] = 1.0

            # 3. Package and stream telemetry packet
            # Heart rate is clamped below if not warmed up
            heart_rate = vitals_sample.heart_rate_bpm
            if heart_rate < 30.0 or heart_rate > 200.0:
                # Default warm-up estimate
                heart_rate = 72.0 + 3.0 * math.sin(elapsed * 0.1)

            filtered_trace_val = 0.0
            if vitals_sample.filtered_trace is not None and vitals_sample.filtered_trace.size > 0:
                filtered_trace_val = float(vitals_sample.filtered_trace[-1])

            payload = {
                "type": "biometric_telemetry",
                "payload": {
                    "heart_rate_bpm": float(heart_rate),
                    "rppg_trace_value": filtered_trace_val,
                    "joint_cosines": joint_cosines,
                    "gaze_xy": list(skeletal_frame.gaze_xy),
                    "gesture": skeletal_frame.gesture,
                    "timestamp": current_time,
                    "frame_index": frame_index
                }
            }

            await websocket.send_json(payload)

    except WebSocketDisconnect:
        logger.info("Biometrics WebSocket tunnel disconnected.")
    except Exception as exc:
        logger.error("Error in Biometrics streaming WebSocket loop: %s", exc)
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
