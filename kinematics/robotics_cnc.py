"""Denavit-Hartenberg robotic kinematics and actuator interlock checks."""

from __future__ import annotations

import logging
import math
import threading
import time
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np

logger = logging.getLogger("SPARK_KINEMATICS")


class RobotKinematicsSolver:
    """Analytical DH solver with optional torque interlock monitoring."""

    def __init__(self, link_lengths: Tuple[float, float, float] = (10.0, 10.0, 5.0), torque_limit: float = 3.5) -> None:
        self.l1, self.l2, self.l3 = (float(v) for v in link_lengths)
        self.torque_limit = float(torque_limit)
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitor_running = False

    def get_link_transform(self, theta: float, d: float, a: float, alpha: float) -> np.ndarray:
        ct, st = math.cos(theta), math.sin(theta)
        ca, sa = math.cos(alpha), math.sin(alpha)
        return np.array(
            [
                [ct, -st * ca, st * sa, a * ct],
                [st, ct * ca, -ct * sa, a * st],
                [0.0, sa, ca, d],
                [0.0, 0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )

    def forward_kinematics(self, joint_angles: Tuple[float, float, float]) -> Tuple[float, float, float]:
        t1, t2, t3 = (float(v) for v in joint_angles)
        t01 = self.get_link_transform(t1, self.l1, 0.0, math.pi / 2.0)
        t12 = self.get_link_transform(t2, 0.0, self.l2, 0.0)
        t23 = self.get_link_transform(t3, 0.0, self.l3, 0.0)
        t03 = t01 @ t12 @ t23
        return float(t03[0, 3]), float(t03[1, 3]), float(t03[2, 3])

    def inverse_kinematics(self, target_xyz: Tuple[float, float, float] | np.ndarray) -> Tuple[float, float, float]:
        x, y, z = (float(v) for v in np.asarray(target_xyz, dtype=np.float64).reshape(3))
        theta1 = math.atan2(y, x)
        r = math.sqrt(x**2 + y**2)
        z_shifted = z - self.l1
        d_sq = r**2 + z_shifted**2
        d = math.sqrt(d_sq)

        reach_max = self.l2 + self.l3
        reach_min = abs(self.l2 - self.l3)
        if d > reach_max or d < reach_min:
            raise ValueError(f"Target coordinate ({x}, {y}, {z}) is outside robot workspace limits.")

        cos_theta3 = (d_sq - self.l2**2 - self.l3**2) / (2.0 * self.l2 * self.l3)
        cos_theta3 = max(-1.0, min(1.0, cos_theta3))
        theta3 = math.acos(cos_theta3)
        a = self.l2 + self.l3 * cos_theta3
        b = self.l3 * math.sin(theta3)
        theta2 = math.atan2(z_shifted * a - r * b, r * a + z_shifted * b)
        return float(theta1), float(theta2), float(theta3)

    def solve_cartesian_targets(self, targets: np.ndarray) -> List[Dict[str, Any]]:
        array = np.asarray(targets, dtype=np.float64)
        if array.ndim == 1:
            array = array.reshape(1, -1)
        if array.shape[-1] != 3:
            raise ValueError("Cartesian targets must have shape (n, 3).")
        results = []
        for target in array:
            theta = self.inverse_kinematics(tuple(float(v) for v in target))
            results.append(
                {
                    "target_xyz": [float(v) for v in target],
                    "joint_angles_rad": list(theta),
                    "joint_angles_deg": [math.degrees(v) for v in theta],
                    "fk_xyz": list(self.forward_kinematics(theta)),
                }
            )
        return results

    def check_torque_interlock(
        self,
        current_draw: float,
        torque_constant: float,
        emergency_callback: Optional[Callable[[str], None]] = None,
        label: str = "robotic_actuator",
    ) -> bool:
        torque_estimate = float(current_draw) * float(torque_constant)
        if torque_estimate > self.torque_limit:
            message = f"Torque interlock triggered for {label}: {torque_estimate:.3f} > {self.torque_limit:.3f}"
            if emergency_callback:
                emergency_callback(message)
            else:
                try:
                    from api.server import broadcast_system_alert

                    broadcast_system_alert(
                        {
                            "source": "robotics_cnc",
                            "severity": "critical",
                            "message": message,
                            "label": label,
                        }
                    )
                except Exception:
                    pass
            raise RuntimeError(message)
        return True

    def start_torque_monitor(
        self,
        telemetry_source: Callable[[], Dict[str, float]],
        emergency_callback: Optional[Callable[[str], None]] = None,
        poll_interval_seconds: float = 0.05,
    ) -> None:
        if self._monitor_running:
            return

        self._monitor_running = True

        def _loop() -> None:
            while self._monitor_running:
                try:
                    telemetry = telemetry_source()
                    current_draw = float(telemetry.get("current_draw", 0.0))
                    torque_constant = float(telemetry.get("torque_constant", 1.0))
                    self.check_torque_interlock(current_draw, torque_constant, emergency_callback)
                except Exception as exc:
                    logger.error("Torque monitor fault: %s", exc)
                    if emergency_callback:
                        try:
                            emergency_callback(str(exc))
                        except Exception:
                            pass
                time.sleep(max(0.01, float(poll_interval_seconds)))

        self._monitor_thread = threading.Thread(target=_loop, daemon=True, name="spark-torque-monitor")
        self._monitor_thread.start()

    def stop_torque_monitor(self) -> None:
        self._monitor_running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
            self._monitor_thread = None


class SafetyInterlockMonitor:
    def __init__(self, current_ceiling_amps: float = 3.5):
        self.ceiling = float(current_ceiling_amps)
        self.emergency_halt_active = False

    def check_motor_current(self, current_reading: float, emergency_callback: Callable[[], None]) -> bool:
        if float(current_reading) > self.ceiling:
            self.emergency_halt_active = True
            logger.critical("TORQUE PROTECTION TRIP: Current reading %.2fA exceeded safety limit %.2fA!", current_reading, self.ceiling)
            emergency_callback()
            return True
        return False


from generative.mesh_slicer import CNCSlicerEngine


DHKinematicsSolver = RobotKinematicsSolver
