"""Compound swarm workflow orchestration for CAD, slicing, and kinematics."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from core.hardware_bridge import HardwareAgentBridge
from generative.mesh_slicer import MeshContourSlicer
from kinematics.robotics_cnc import RobotKinematicsSolver

logger = logging.getLogger("SPARK_SWARM_WORKFLOW")


def _broadcast_system_alert(payload: dict[str, Any]) -> None:
    try:
        from api.server import broadcast_system_alert

        broadcast_system_alert(payload)
    except Exception:
        pass


def _coerce_float(value: Any, default: float) -> float:
    try:
        if value is None:
            return float(default)
        return float(value)
    except Exception:
        return float(default)


def _first_float(text: str, names: tuple[str, ...], default: float) -> float:
    for name in names:
        match = re.search(rf"\b{name}\s*[:=]\s*(-?[0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
        if match:
            return _coerce_float(match.group(1), default)
    return float(default)


def _parse_coordinates(text: str, fallback: dict[str, float]) -> dict[str, float]:
    coords = dict(fallback)
    for axis in ("x", "y", "z"):
        match = re.search(rf"\b{axis}\s*[:=]\s*(-?[0-9]+(?:\.[0-9]+)?)", text, flags=re.IGNORECASE)
        if match:
            coords[axis] = _coerce_float(match.group(1), coords.get(axis, 0.0))
    return coords


@dataclass(slots=True)
class WorkflowResult:
    status: str
    step: str
    result: dict[str, Any]


class SwarmWorkflowEngine:
    """Sequential macro-task orchestrator for CAD, slicing, and kinematics."""

    def __init__(
        self,
        bridge: Optional[HardwareAgentBridge] = None,
        slicer: Optional[MeshContourSlicer] = None,
        kinematics_solver: Optional[RobotKinematicsSolver] = None,
    ) -> None:
        self.bridge = bridge or HardwareAgentBridge()
        self.slicer = slicer or MeshContourSlicer(layer_height=0.2)
        self.kinematics_solver = kinematics_solver or RobotKinematicsSolver()

    def _build_geometry(self, cad_result: dict[str, Any]) -> tuple[np.ndarray, np.ndarray]:
        density_shape = cad_result.get("density_shape") or [8, 12, 24]
        if isinstance(density_shape, (list, tuple)) and len(density_shape) >= 3:
            scale = max(1.0, float(density_shape[0]))
        else:
            scale = 1.0

        vertices = np.array(
            [
                [0.0, 0.0, 0.0],
                [scale, 0.0, 0.0],
                [scale, scale, 0.0],
                [0.0, 0.0, scale * self.slicer.layer_height],
            ],
            dtype=np.float64,
        )
        faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
        return vertices, faces

    def execute(self, user_request: str, runtime_context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        runtime_context = runtime_context or {}
        request_text = str(user_request or "").strip()

        volume_fraction = runtime_context.get("volume_fraction")
        compliance_target = runtime_context.get("compliance_target")
        target_coordinates = runtime_context.get("target_coordinates") or {}
        current_draw = _coerce_float(runtime_context.get("current_draw", 1.0), 1.0)
        torque_constant = _coerce_float(runtime_context.get("torque_constant", 1.0), 1.0)

        if not isinstance(target_coordinates, dict):
            target_coordinates = {}

        target_coordinates = _parse_coordinates(
            request_text,
            {
                "x": 5.0,
                "y": 5.0,
                "z": 15.0,
                **{k: _coerce_float(v, 0.0) for k, v in target_coordinates.items() if isinstance(v, (int, float, str))},
            },
        )
        volume_fraction = _coerce_float(volume_fraction, _first_float(request_text, ("volume_fraction", "volfrac"), 0.4))
        compliance_target = _coerce_float(compliance_target, _first_float(request_text, ("compliance_target", "compliance"), 1e5))

        logger.info("Swarm workflow starting: request=%r", request_text)

        try:
            cad_result = self.bridge.optimize_cad_topology(
                volume_fraction=volume_fraction,
                compliance_target=compliance_target,
            )
        except Exception as exc:
            message = f"CAD optimization failed: {exc}"
            _broadcast_system_alert({"source": "swarm_workflow_engine", "type": "cad_error", "message": message, "severity": "critical"})
            return {"status": "halted", "step": "optimize_cad_topology", "result": {"message": message}}

        if cad_result.get("status") == "error":
            message = str(cad_result.get("message", "CAD optimization error"))
            _broadcast_system_alert({"source": "swarm_workflow_engine", "type": "cad_error", "message": message, "severity": "critical"})
            return {"status": "halted", "step": "optimize_cad_topology", "result": cad_result}

        vertices, faces = self._build_geometry(cad_result)

        try:
            gcode = self.slicer.slice_mesh(vertices, faces)
        except Exception as exc:
            message = f"Mesh slicing failed: {exc}"
            _broadcast_system_alert({"source": "swarm_workflow_engine", "type": "slice_error", "message": message, "severity": "critical"})
            return {"status": "halted", "step": "slice_mesh", "result": {"message": message}}

        try:
            kinematics_result = self.bridge.solve_robot_kinematics(
                x=_coerce_float(target_coordinates.get("x", 5.0), 5.0),
                y=_coerce_float(target_coordinates.get("y", 5.0), 5.0),
                z=_coerce_float(target_coordinates.get("z", 15.0), 15.0),
            )
        except Exception as exc:
            message = f"Kinematics solve failed: {exc}"
            _broadcast_system_alert({"source": "swarm_workflow_engine", "type": "kinematics_error", "message": message, "severity": "critical"})
            return {"status": "halted", "step": "solve_robot_kinematics", "result": {"message": message}}

        if kinematics_result.get("status") == "error":
            message = str(kinematics_result.get("message", "Kinematics boundary error"))
            _broadcast_system_alert({"source": "swarm_workflow_engine", "type": "kinematics_error", "message": message, "severity": "critical"})
            return {"status": "halted", "step": "solve_robot_kinematics", "result": kinematics_result}

        try:
            self.kinematics_solver.check_torque_interlock(
                current_draw=current_draw,
                torque_constant=torque_constant,
                label="swarm_workflow",
            )
        except Exception as exc:
            message = str(exc)
            _broadcast_system_alert({"source": "swarm_workflow_engine", "type": "torque_check", "message": message, "severity": "critical"})
            return {"status": "halted", "step": "torque_check", "result": {"message": message}}

        return {
            "status": "success",
            "step": "complete",
            "result": {
                "cad": cad_result,
                "gcode_lines": len(gcode),
                "gcode_preview": gcode[:5],
                "kinematics": kinematics_result,
            },
        }

    async def run(self, user_request: str, runtime_context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        import asyncio

        return await asyncio.to_thread(self.execute, user_request, runtime_context)
