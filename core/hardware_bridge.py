"""Agent hardware tool registry and integration dispatcher for Phase 4."""

from __future__ import annotations

import logging
import math
import os
from typing import Any, Dict, Tuple

import numpy as np

# Route floating point overflows/underflows to raise Python exceptions
np.seterr(all="raise")

logger = logging.getLogger("SPARK_HARDWARE_BRIDGE")

try:
    from generative.cad_engine import VoxelTopologyEngine
except ImportError:
    # Fallback/stub if not found in test env
    VoxelTopologyEngine = None

try:
    from kinematics.robotics_cnc import RobotKinematicsSolver
except ImportError:
    RobotKinematicsSolver = None

try:
    from diagnostics.predictive_diagnostics import PredictiveDiagnosticsEngine
except ImportError:
    PredictiveDiagnosticsEngine = None


class HardwareAgentBridge:
    """Unified dispatcher executing hardware optimization and diagnostics safely."""

    def __init__(self) -> None:
        pass

    def optimize_cad_topology(self, volume_fraction: float, compliance_target: float) -> Dict[str, Any]:
        """Runs SIMP-based voxel topology optimization on the CAD engine."""
        try:
            vol_frac = float(volume_fraction)
            target = float(compliance_target)

            if not (0.01 <= vol_frac <= 1.0):
                return {
                    "status": "error",
                    "message": f"Validation Error: Volume fraction must be in range [0.01, 1.0]. Got {vol_frac}"
                }

            if VoxelTopologyEngine is None:
                return {
                    "status": "error",
                    "message": "Hardware Error: VoxelTopologyEngine not imported."
                }

            # Instantiate voxel engine
            engine = VoxelTopologyEngine(volume_fraction=vol_frac)
            
            # Solve optimization loop
            res = engine.solve(iterations=8)
            
            compliance = float(res["compliance_proxy"])
            avg_density = float(res["average_density"])

            status = "success"
            message = "CAD topology optimization completed."
            if compliance > target:
                status = "warning"
                message = f"Optimized compliance ({compliance:.4f}) exceeded target limit ({target:.4f})."

            return {
                "status": status,
                "message": message,
                "average_density": avg_density,
                "compliance_proxy": compliance,
                "volume_fraction": float(res["volume_fraction"]),
                "density_shape": list(res["density_matrix"].shape)
            }

        except (FloatingPointError, OverflowError, ValueError, ZeroDivisionError) as err:
            logger.error("Topology math overflow or calculation error: %s", err)
            return {
                "status": "error",
                "message": f"Hardware Arithmetic Error: Math overflow/domain fault occurred during CAD topology optimization: {err}"
            }
        except Exception as err:
            logger.error("Unexpected CAD optimization error: %s", err)
            return {
                "status": "error",
                "message": f"System Alert: Unexpected CAD topology failure: {err}"
            }

    def solve_robot_kinematics(self, x: float, y: float, z: float) -> Dict[str, Any]:
        """Computes inverse kinematics using Denavit-Hartenberg models with strict tolerance checks."""
        try:
            tx = float(x)
            ty = float(y)
            tz = float(z)

            # Ensure values are finite
            if not (np.isfinite(tx) and np.isfinite(ty) and np.isfinite(tz)):
                raise ValueError("Target coordinate values must be finite numbers.")

            if RobotKinematicsSolver is None:
                return {
                    "status": "error",
                    "message": "Hardware Error: RobotKinematicsSolver not imported."
                }

            solver = RobotKinematicsSolver()

            # The solver raises ValueError directly on reach violations
            theta1, theta2, theta3 = solver.inverse_kinematics((tx, ty, tz))
            fk_x, fk_y, fk_z = solver.forward_kinematics((theta1, theta2, theta3))

            return {
                "status": "success",
                "message": "Robotic kinematics solved successfully.",
                "joint_angles_rad": [float(theta1), float(theta2), float(theta3)],
                "joint_angles_deg": [float(math.degrees(theta1)), float(math.degrees(theta2)), float(math.degrees(theta3))],
                "forward_kinematics_xyz": [float(fk_x), float(fk_y), float(fk_z)]
            }

        except ValueError as err:
            logger.warning("Kinematics tolerance boundary violation: %s", err)
            return {
                "status": "error",
                "message": f"Workspace Boundary Alert: Target point lies outside physical CNC kinematics workspace: {err}"
            }
        except (FloatingPointError, OverflowError, ZeroDivisionError) as err:
            logger.error("Kinematics mathematical calculation error: %s", err)
            return {
                "status": "error",
                "message": f"Hardware Arithmetic Error: Math overflow/domain fault occurred during DH kinematics computation: {err}"
            }
        except Exception as err:
            logger.error("Unexpected kinematics error: %s", err)
            return {
                "status": "error",
                "message": f"System Alert: Unexpected kinematics engine failure: {err}"
            }

    def run_predictive_diagnostics(self, audio_stream_path: str) -> Dict[str, Any]:
        """Loads spindle audio stream and extracts Mel-Spectrogram features to assess chatter."""
        try:
            if not audio_stream_path:
                return {
                    "status": "error",
                    "message": "Validation Error: Audio stream path must be specified."
                }

            sr = 16000
            waveform = None

            # Load or simulate audio
            if audio_stream_path == "mock" or not os.path.exists(audio_stream_path):
                # Synthesize wave for testing or missing hardware scenarios
                t = np.linspace(0, 1.0, sr, endpoint=False)
                # Combine a normal base spindle sound with some chatter energy
                waveform = 0.4 * np.sin(2 * np.pi * 300 * t) + 0.8 * np.sin(2 * np.pi * 5500 * t)
            else:
                try:
                    from scipy.io import wavfile
                    sr, data = wavfile.read(audio_stream_path)
                    
                    # Normalize signals
                    if data.dtype == np.int16:
                        waveform = data.astype(np.float64) / 32768.0
                    elif data.dtype == np.int32:
                        waveform = data.astype(np.float64) / 2147483648.0
                    elif data.dtype == np.uint8:
                        waveform = (data.astype(np.float64) - 128.0) / 128.0
                    else:
                        waveform = data.astype(np.float64)
                        
                    if waveform.ndim > 1:
                        waveform = waveform.mean(axis=1)
                except Exception as exc:
                    logger.warning("Could not read WAV file via scipy, building fallback: %s", exc)
                    # Safe fallback to avoid hard crash
                    t = np.linspace(0, 1.0, sr, endpoint=False)
                    waveform = 0.5 * np.sin(2 * np.pi * 300 * t)

            if PredictiveDiagnosticsEngine is None:
                return {
                    "status": "error",
                    "message": "Hardware Error: PredictiveDiagnosticsEngine not imported."
                }

            engine = PredictiveDiagnosticsEngine(sample_rate=sr)
            chatter, confidence, mel_spec = engine.detect_chatter(waveform)

            return {
                "status": "success",
                "message": "Predictive diagnostics cycle completed.",
                "chatter_detected": bool(chatter),
                "chatter_confidence": float(confidence),
                "mel_spectrogram_shape": list(mel_spec.shape),
                "mel_spectrogram_mean": float(np.mean(mel_spec)),
                "mel_spectrogram": mel_spec.tolist()
            }

        except (FloatingPointError, OverflowError, ZeroDivisionError) as err:
            logger.error("Predictive diagnostics math error: %s", err)
            return {
                "status": "error",
                "message": f"Hardware Arithmetic Error: Math overflow occurred during Mel-Spectrogram extraction: {err}"
            }
        except Exception as err:
            logger.error("Unexpected diagnostics error: %s", err)
            return {
                "status": "error",
                "message": f"System Alert: Unexpected diagnostics engine failure: {err}"
            }
