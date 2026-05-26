"""
S.P.A.R.K Robotics Orchestration & CNC Control Core
Provides multi-axis kinematics (DH parameters, Forward/Inverse Kinematics),
local mesh slicing and G-code compilation, and torque current safety monitors.
"""

import time
import logging
import math
import numpy as np
from typing import Dict, List, Any, Tuple, Optional, Callable

logger = logging.getLogger("SPARK_ROBOTICS")

class DHKinematicsSolver:
    """
    Solves Forward and Inverse Kinematics for serial link manipulators
    using Denavit-Hartenberg (DH) parameter conventions.
    """
    def __init__(self, link_lengths: Tuple[float, float, float] = (10.0, 10.0, 5.0)):
        self.l1, self.l2, self.l3 = link_lengths

    def get_link_transform(self, theta: float, d: float, a: float, alpha: float) -> np.ndarray:
        """Computes the 4x4 DH transformation matrix for a single link joint."""
        ct, st = math.cos(theta), math.sin(theta)
        ca, sa = math.cos(alpha), math.sin(alpha)
        
        return np.array([
            [ct, -st * ca,  st * sa, a * ct],
            [st,  ct * ca, -ct * sa, a * st],
            [0.0, sa,      ca,       d],
            [0.0, 0.0,     0.0,      1.0]
        ])

    def forward_kinematics(self, joint_angles: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Maps joint angles (theta1, theta2, theta3) to Cartesian (x, y, z)."""
        t1, t2, t3 = joint_angles
        
        # Define DH parameters: (theta, d, a, alpha)
        T01 = self.get_link_transform(t1, self.l1, 0.0, math.pi / 2.0)
        T12 = self.get_link_transform(t2, 0.0, self.l2, 0.0)
        T23 = self.get_link_transform(t3, 0.0, self.l3, 0.0)
        
        T03 = T01 @ T12 @ T23
        
        # Position vector in base frame
        x, y, z = T03[0, 3], T03[1, 3], T03[2, 3]
        return float(x), float(y), float(z)

    def inverse_kinematics(self, target_xyz: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """
        Calculates joint angles (theta1, theta2, theta3) from Cartesian coordinates.
        Uses a geometric solution for 3DOF planar/articulated arms.
        """
        x, y, z = target_xyz
        
        # Base angle (rotation around z-axis)
        theta1 = math.atan2(y, x)
        
        # Shift origin to joint 1
        r = math.sqrt(x**2 + y**2)
        z_shifted = z - self.l1
        
        # Find distance to joint 3
        d_sq = r**2 + z_shifted**2
        d = math.sqrt(d_sq)
        
        # Check workspace limits
        reach_max = self.l2 + self.l3
        reach_min = abs(self.l2 - self.l3)
        if d > reach_max or d < reach_min:
            raise ValueError(f"Target coordinate ({x}, {y}, {z}) is outside robot workspace limits.")
            
        # Cosine rule for joint angles
        cos_theta3 = (d_sq - self.l2**2 - self.l3**2) / (2.0 * self.l2 * self.l3)
        # Numerical boundary cleaning
        cos_theta3 = max(-1.0, min(1.0, cos_theta3))
        theta3 = math.acos(cos_theta3)
        
        # Solve for joint 2 angle algebraically using the chosen theta3
        A = self.l2 + self.l3 * cos_theta3
        B = self.l3 * math.sin(theta3)
        theta2 = math.atan2(z_shifted * A - r * B, r * A + z_shifted * B)
        
        return float(theta1), float(theta2), float(theta3)

class CNCSlicerEngine:
    """Local slicer compiling raw 3D mesh vectors to optimized G-code strings."""
    
    def __init__(self, layer_height: float = 0.2, feed_rate: float = 1200.0, spindle_speed: float = 5000.0):
        self.layer_height = layer_height
        self.feed_rate = feed_rate
        self.spindle_speed = spindle_speed

    def slice_mesh(self, vertices: np.ndarray, faces: np.ndarray) -> List[str]:
        """Slices mesh layers and outputs G-code machine commands."""
        gcode = []
        
        # 1. Header initialization block
        gcode.append("; S.P.A.R.K. CNC Slice Engine Output")
        gcode.append("G21 ; Set units to millimeters")
        gcode.append("G90 ; Absolute coordinates positioning")
        gcode.append(f"M3 S{self.spindle_speed} ; Start spindle motor")
        
        # Find bounding limits
        z_min, z_max = np.min(vertices[:, 2]), np.max(vertices[:, 2])
        layers = np.arange(z_min + self.layer_height, z_max + self.layer_height, self.layer_height)
        
        # Simple contour generation loop representing layers
        # In full production, we intersect planes at z with triangles.
        # Here we slice coordinates to outline basic circular/rectangular boundary envelopes.
        for layer_z in layers:
            gcode.append(f"; Slicing Layer Z={layer_z:.2f}")
            # Retract tool, travel to layer z
            gcode.append(f"G0 Z{layer_z + 2.0:.2f} F{self.feed_rate}")
            
            # Simple circular pattern representation for testing toolpaths
            radius = 10.0
            gcode.append(f"G0 X{radius:.2f} Y0.00 Z{layer_z:.2f} ; Initial engagement")
            for angle in np.linspace(0.1, 2.0 * math.pi, num=12):
                x_pos = radius * math.cos(angle)
                y_pos = radius * math.sin(angle)
                gcode.append(f"G1 X{x_pos:.2f} Y{y_pos:.2f} F{self.feed_rate} ; Tool engagement path")
                
        # Footer return home commands
        gcode.append("M5 ; Stop spindle motor")
        gcode.append("G28 ; Home axes")
        logger.info(f"Slicing complete. G-code lines generated: {len(gcode)}")
        return gcode

class SafetyInterlockMonitor:
    """Monitors active motor currents and runs asynchronous safety halts."""
    
    def __init__(self, current_ceiling_amps: float = 3.5):
        self.ceiling = current_ceiling_amps
        self.emergency_halt_active = False

    def check_motor_current(self, current_reading: float, emergency_callback: Callable[[], None]) -> bool:
        """Polls active device current, tripping safety callback if ceilings are breached."""
        if current_reading > self.ceiling:
            self.emergency_halt_active = True
            logger.critical(f"TORQUE PROTECTION TRIP: Current reading {current_reading:.2f}A exceeded safety limit {self.ceiling}A!")
            # Trigger immediate safety shutdown callback
            emergency_callback()
            return True
        return False
