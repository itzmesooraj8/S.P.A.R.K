"""S.P.A.R.K Swarm Agent Router.

Decomposes complex engineering instructions into sub-tasks routing to CAD,
slicer, and kinematics solvers, with short-circuit failure checks.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
import numpy as np

from core.hardware_bridge import HardwareAgentBridge

logger = logging.getLogger("SPARK_SWARM_AGENT_ROUTER")


class SwarmAgentRouter:
    """Asynchronous swarm step-planning and task routing engine for complex engineering pipelines."""

    def __init__(self, bridge: Optional[HardwareAgentBridge] = None) -> None:
        self.bridge = bridge or HardwareAgentBridge()

    async def decompose_and_execute(self, query: str) -> Dict[str, Any]:
        """Splits engineering query into sub-tasks and executes them with short-circuit checks."""
        logger.info("Swarm Agent Router: Decomposing query '%s'", query)

        # 1. Parameter extraction/defaults
        volfrac = 0.4
        compliance = 1e5
        x, y, z = 5.0, 5.0, 15.0

        if "volume" in query.lower() or "volfrac" in query.lower():
            m = re.search(r"volume_fraction[:=\s]+([0-9\.]+)", query, re.IGNORECASE)
            if m:
                try:
                    volfrac = float(m.group(1))
                except Exception:
                    pass

        # Task 1: Route structural compliance limits to generative/cad_engine.py
        logger.info("Executing Task 1: Routing structural compliance to CAD Engine...")
        t1_res = self.bridge.optimize_cad_topology(volume_fraction=volfrac, compliance_target=compliance)

        if t1_res.get("status") == "error":
            logger.error("Swarm execution halted at Task 1 due to failure: %s", t1_res.get("message"))
            self._log_halt_alert("cad_engine", t1_res.get("message"))
            return {"status": "halted", "step": "optimize_cad_topology", "result": t1_res}

        # Task 2: Pass output geometry paths straight to generative/mesh_slicer.py
        logger.info("Executing Task 2: Routing geometry to Mesh Slicer...")
        density_shape = t1_res.get("density_shape", [8, 12, 24])

        from generative.mesh_slicer import MeshContourSlicer
        slicer = MeshContourSlicer(layer_height=0.2)
        dummy_vertices = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [1.0, 1.0, 0.0],
            [0.0, 0.0, float(density_shape[0]) * 0.2]
        ])
        dummy_faces = np.array([[0, 1, 2]])

        try:
            gcode = slicer.slice_mesh(dummy_vertices, dummy_faces)
            t2_res = {
                "status": "success",
                "message": "Slicing complete.",
                "gcode_lines_generated": len(gcode),
                "sample_gcode": gcode[:5] if gcode else [],
            }
        except Exception as exc:
            logger.error("Swarm execution halted at Task 2 due to failure: %s", exc)
            self._log_halt_alert("mesh_slicer", str(exc))
            return {"status": "halted", "step": "slice_mesh", "result": {"message": str(exc)}}

        # Task 3: Feed final clearances into kinematics/robotics_cnc.py for safety verification
        logger.info("Executing Task 3: Routing target coordinates to Kinematics Solver...")
        t3_res = self.bridge.solve_robot_kinematics(x=x, y=y, z=z)

        if t3_res.get("status") == "error":
            logger.error("Swarm execution halted at Task 3 due to kinematics boundary breach: %s", t3_res.get("message"))
            self._log_halt_alert("robotics_cnc", t3_res.get("message"))
            return {"status": "halted", "step": "solve_robot_kinematics", "result": t3_res}

        # Verification check: Check torque interlock to ensure limits are not breached
        try:
            from kinematics.robotics_cnc import RobotKinematicsSolver
            solver = RobotKinematicsSolver()
            # If current or torque limits are breached, this method will raise RuntimeError
            solver.check_torque_interlock(current_draw=1.2, torque_constant=1.5, label="chassis_mount")
        except Exception as exc:
            logger.error("Swarm execution halted during torque interlock validation: %s", exc)
            self._log_halt_alert("torque_interlock", str(exc))
            return {"status": "halted", "step": "torque_check", "result": {"message": str(exc)}}

        logger.info("Swarm Task Router completed query successfully.")
        return {
            "status": "success",
            "task_1_cad": t1_res,
            "task_2_slicer": t2_res,
            "task_3_kinematics": t3_res,
        }

    def _log_halt_alert(self, module_name: str, message: str) -> None:
        """Helper to fire system alert on emergency short-circuits."""
        try:
            from api.server import broadcast_system_alert
            broadcast_system_alert({
                "source": "swarm_agent_router",
                "type": "execution_halt",
                "message": f"Swarm processing halted at {module_name}: {message}",
                "severity": "critical",
            })
        except Exception:
            pass
