import asyncio
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from core.db_partitioner import DatabasePartitioner
from core.persona_manager import PersonaManager
from core.session_archivist import SessionContextArchivist
from core.swarm_workflow_engine import SwarmWorkflowEngine
from diagnostics.fluid_flow_monitor import FluidFlowMonitor
from security.session_authorization import authorize_sensitive_tool
from security.intent_validator import validate_intent_text


class TestSwarmWorkflow(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.mkdtemp()
        self.sandbox_root = Path(self.temp_dir, "sandbox")
        self.sandbox_root.mkdir(parents=True, exist_ok=True)
        self.partition_dir = Path(self.temp_dir, "partitions")
        self.partition_dir.mkdir(parents=True, exist_ok=True)
        self.partitioner = DatabasePartitioner(partition_dir=str(self.partition_dir))
        self.archivist = SessionContextArchivist(partitioner=self.partitioner, token_threshold=16)

    def tearDown(self) -> None:
        self.partitioner.close()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_intent_filler_cleanup(self) -> None:
        scan = validate_intent_text("alright no but look, optimize the chassis and slice it")
        self.assertTrue(scan.allowed)
        self.assertIn("optimize", scan.cleaned_text.lower())
        self.assertNotIn("alright", scan.cleaned_text.lower())

    def test_swarm_workflow_tool_registered(self) -> None:
        from core.spark_brain import TOOLS

        tool_names = [tool.get("function", {}).get("name") for tool in TOOLS if isinstance(tool, dict)]
        self.assertIn("run_swarm_workflow", tool_names)

    def test_persona_identity_block(self) -> None:
        persona = PersonaManager(selected_persona="spark").get_selected_persona()
        block = PersonaManager(selected_persona="spark").build_system_block()

        self.assertEqual(persona.name, "S.P.A.R.K.")
        self.assertEqual(persona.backronym, "Smart Processing and Adaptive Reasoning Kernel")
        self.assertIn("S.P.A.R.K.", block)
        self.assertIn("Smart Processing and Adaptive Reasoning Kernel", block)
        self.assertNotIn("JARVIS", block)

    def test_session_token_allows_sensitive_tool(self) -> None:
        with patch.dict("os.environ", {"SPARK_SESSION_TOKEN": "unit-test-token", "SPARK_SESSION_TOKEN_TTL_SECONDS": "60"}, clear=False):
            auth = authorize_sensitive_tool("get_network_connections", prompt=False)

        self.assertTrue(auth.allowed)
        self.assertIn(auth.reason, {"session_token", "session_context", "ephemeral_confirmation"})

    @patch("core.swarm_workflow_engine.RobotKinematicsSolver.check_torque_interlock")
    @patch("core.swarm_workflow_engine.MeshContourSlicer.slice_mesh")
    @patch("core.swarm_workflow_engine.HardwareAgentBridge")
    def test_swarm_workflow_success(self, mock_bridge_class, mock_slice_mesh, mock_torque_check) -> None:
        mock_bridge = MagicMock()
        mock_bridge.optimize_cad_topology.return_value = {"status": "success", "density_shape": [8, 12, 24]}
        mock_bridge.solve_robot_kinematics.return_value = {"status": "success", "solution": [1.0, 2.0, 3.0]}
        mock_bridge_class.return_value = mock_bridge
        mock_slice_mesh.return_value = ["G0 X0.000 Y0.000 Z0.000 F1200", "G1 X1.000 Y1.000 Z0.000 F1200"]
        mock_torque_check.return_value = True

        engine = SwarmWorkflowEngine(bridge=mock_bridge)
        result = engine.execute(
            "Optimize and slice the design for x=6 y=7 z=8 volume_fraction=0.35 compliance_target=2500",
            runtime_context={"current_draw": 1.0, "torque_constant": 1.0},
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["step"], "complete")
        self.assertIn("cad", result["result"])
        self.assertIn("kinematics", result["result"])
        self.assertEqual(result["result"]["gcode_lines"], 2)
        self.assertIn("S.P.A.R.K.", PersonaManager(selected_persona="spark").build_system_block())
        mock_bridge.optimize_cad_topology.assert_called_once()
        mock_bridge.solve_robot_kinematics.assert_called_once()
        mock_torque_check.assert_called_once()

    @patch("api.server.broadcast_system_alert")
    @patch("core.swarm_workflow_engine.RobotKinematicsSolver.check_torque_interlock", side_effect=RuntimeError("Torque limit exceeded"))
    @patch("core.swarm_workflow_engine.MeshContourSlicer.slice_mesh")
    @patch("core.swarm_workflow_engine.HardwareAgentBridge")
    def test_torque_short_circuit(self, mock_bridge_class, mock_slice_mesh, mock_torque_check, mock_alert) -> None:
        mock_bridge = MagicMock()
        mock_bridge.optimize_cad_topology.return_value = {"status": "success", "density_shape": [8, 12, 24]}
        mock_bridge.solve_robot_kinematics.return_value = {"status": "success"}
        mock_bridge_class.return_value = mock_bridge
        mock_slice_mesh.return_value = ["G0 X0.000 Y0.000 Z0.000 F1200"]

        engine = SwarmWorkflowEngine(bridge=mock_bridge)
        result = engine.execute("Optimize then verify torque", runtime_context={"current_draw": 3.5, "torque_constant": 3.0})

        self.assertEqual(result["status"], "halted")
        self.assertEqual(result["step"], "torque_check")
        self.assertIn("Torque limit exceeded", result["result"]["message"])
        self.assertTrue(mock_alert.called)

    @patch("core.workspace_generator.subprocess.Popen")
    @patch("core.spark_brain.client", None)
    @patch("core.spark_brain._local_chat_completion")
    def test_manifest_compiles_into_sandbox(self, mock_local_complete, mock_popen) -> None:
        from core import workspace_generator

        mock_local_complete.return_value = json.dumps(
            {
                "project_name": "healthcare_portal",
                "frameworks": ["vanilla"],
                "block_locations": {"header": "top", "content": "middle", "footer": "bottom"},
                "view_parameters": {"theme": "dark", "viewport": "width=device-width, initial-scale=1.0"},
                "files": [
                    {"path": "profiles/index.html", "content": "<html><body>hello</body></html>"},
                    {"path": "profiles/app.js", "content": "console.log('ok');"},
                ],
            }
        )

        sandbox_override = Path(self.sandbox_root, "compiled")
        with patch.object(workspace_generator, "SANDBOX_DIR", sandbox_override):
            result = asyncio.run(workspace_generator.generate_workspace("healthcare portal", "build a healthcare app"))

        self.assertEqual(result["status"], "success")
        self.assertTrue(all(str(path).startswith("healthcare_portal") for path in result["created_files"]))
        for relative_path in result["created_files"]:
            self.assertTrue((sandbox_override / relative_path).exists())
            self.assertTrue((sandbox_override / relative_path).resolve().is_relative_to(sandbox_override.resolve()))
        mock_popen.assert_called()

    def test_fluid_flow_monitor_blocks_injection(self) -> None:
        safe_file = self.sandbox_root / "safe.txt"
        safe_file.write_text("steady state", encoding="utf-8")
        bad_file = self.sandbox_root / "bad.py"
        bad_file.write_text("import os\nos.system('whoami')", encoding="utf-8")

        monitor = FluidFlowMonitor(sandbox_root=self.sandbox_root, scan_interval_seconds=0.01)

        with self.assertRaises(PermissionError):
            monitor.scan_once()


if __name__ == "__main__":
    unittest.main()