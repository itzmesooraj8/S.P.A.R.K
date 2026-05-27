import unittest
import asyncio
import os
import shutil
import tempfile
import time
from unittest.mock import patch, MagicMock

from core.session_archivist import SessionContextArchivist
from core.swarm_agent_router import SwarmAgentRouter
from security.sandbox_memory_bridge import SandboxMemoryBridge, SecurityError
from api.server import TelemetryRefresher
from core.db_partitioner import DatabasePartitioner

class TestSwarmIntegration(unittest.TestCase):

    def setUp(self):
        # Create temp dir for partition database and sandbox folder
        self.test_dir = tempfile.mkdtemp()
        self.partition_dir = os.path.join(self.test_dir, "partitions")
        self.sandbox_dir = os.path.join(self.test_dir, "sandbox")
        os.makedirs(self.partition_dir, exist_ok=True)
        os.makedirs(self.sandbox_dir, exist_ok=True)
        
        self.partitioner = DatabasePartitioner(partition_dir=self.partition_dir)
        self.archivist = SessionContextArchivist(partitioner=self.partitioner, token_threshold=20)
        self.bridge = SandboxMemoryBridge(sandbox_root=self.sandbox_dir)

    def tearDown(self):
        self.partitioner.close()
        shutil.rmtree(self.test_dir, ignore_errors=True)

    # === Session Context Archivist Tests ===
    
    def test_session_archivist_save_and_retrieve(self):
        # Run save_turn and verify database query retrieves it
        async def run_test():
            conv_id = "test_conv_123"
            state = {"calibration_value": 42.0, "joint_offsets": [0.01, -0.02, 0.05]}
            await self.archivist.save_turn(
                conversation_id=conv_id,
                role="user",
                content="calibrate system",
                state_metadata=state
            )
            
            history = await self.archivist.get_history(conv_id)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["role"], "user")
            self.assertEqual(history[0]["content"], "calibrate system")
            self.assertEqual(history[0]["metadata"]["calibration_value"], 42.0)
            
            # Verify load_last_calibration_states restores it
            cal_state = await self.archivist.load_last_calibration_states()
            self.assertEqual(cal_state.get("calibration_value"), 42.0)
            self.assertEqual(cal_state.get("joint_offsets"), [0.01, -0.02, 0.05])
            
        asyncio.run(run_test())

    @patch("core.spark_brain.client", None)
    @patch("core.spark_brain._local_chat_completion")
    def test_session_archivist_compression(self, mock_local_complete):
        mock_local_complete.return_value = "Compressed summary of previous calibration instructions."
        
        async def run_test():
            messages = [
                {"role": "system", "content": "You are a calibration helper."},
                {"role": "user", "content": "Please calibrate the spindle motor to 3.5 Amps absolute maximum limit today."},
                {"role": "assistant", "content": "Understood, calibrating spindle to 3.5 Amps."},
                {"role": "user", "content": "Next, align joint kinematics and record calibration coordinates."},
                {"role": "assistant", "content": "Aligning joint kinematics now."}
            ]
            # Since threshold is 20 words, and our messages contain around 30 words, it should compress
            compressed = await self.archivist.compress_history_if_needed("test_conv_comp", messages)
            
            self.assertEqual(compressed[0]["role"], "system") # System prompt kept
            self.assertEqual(compressed[1]["role"], "system") # Compressed message role
            self.assertIn("Compressed summary", compressed[1]["content"])
            # Last two messages are kept
            self.assertEqual(compressed[-2]["role"], "user")
            self.assertEqual(compressed[-1]["role"], "assistant")
            
        asyncio.run(run_test())

    # === Swarm Agent Router Tests ===

    @patch("api.server.broadcast_system_alert")
    def test_swarm_agent_router_success(self, mock_alert):
        router = SwarmAgentRouter()
        
        async def run_test():
            res = await router.decompose_and_execute("Optimize volume fraction 0.35 and verify")
            self.assertEqual(res.get("status"), "success")
            self.assertIn("task_1_cad", res)
            self.assertIn("task_2_slicer", res)
            self.assertIn("task_3_kinematics", res)
            
        asyncio.run(run_test())

    @patch("api.server.broadcast_system_alert")
    def test_swarm_agent_router_short_circuit_cad_error(self, mock_alert):
        # Mock bridge to return error for CAD optimization
        mock_bridge = MagicMock()
        mock_bridge.optimize_cad_topology.return_value = {"status": "error", "message": "Yield stress breach"}
        router = SwarmAgentRouter(bridge=mock_bridge)
        
        async def run_test():
            res = await router.decompose_and_execute("Optimize chassis structural compliance")
            self.assertEqual(res.get("status"), "halted")
            self.assertEqual(res.get("step"), "optimize_cad_topology")
            self.assertEqual(res["result"]["message"], "Yield stress breach")
            
        asyncio.run(run_test())

    @patch("core.swarm_agent_router.HardwareAgentBridge")
    @patch("kinematics.robotics_cnc.RobotKinematicsSolver.check_torque_interlock")
    @patch("api.server.broadcast_system_alert")
    def test_swarm_agent_router_short_circuit_torque_breach(self, mock_alert, mock_interlock, mock_bridge_class):
        # Mock bridge for normal CAD and Kinematics, but fail torque interlock check
        mock_bridge = MagicMock()
        mock_bridge.optimize_cad_topology.return_value = {"status": "success", "density_shape": [8, 12, 24]}
        mock_bridge.solve_robot_kinematics.return_value = {"status": "success"}
        mock_bridge_class.return_value = mock_bridge
        
        mock_interlock.side_effect = RuntimeError("Torque limit exceeded!")
        router = SwarmAgentRouter(bridge=mock_bridge)
        
        async def run_test():
            res = await router.decompose_and_execute("Optimize and check kinematics")
            self.assertEqual(res.get("status"), "halted")
            self.assertEqual(res.get("step"), "torque_check")
            self.assertIn("Torque limit exceeded!", res["result"]["message"])
            
        asyncio.run(run_test())

    # === Sandbox Memory Bridge Tests ===

    def test_sandbox_memory_bridge_read_write(self):
        filename = "worker_state.json"
        data = {"state": "ready", "packet_loss": 0.05}
        self.bridge.write_worker_state(filename, data)
        
        read_data = self.bridge.read_worker_state(filename)
        self.assertEqual(read_data["state"], "ready")
        self.assertEqual(read_data["packet_loss"], 0.05)

    def test_sandbox_memory_bridge_traversal_blocked(self):
        # Attempt to read outside sandbox
        filename = "../../security/signature_verifier.py"
        with self.assertRaises(PermissionError):
            self.bridge.read_worker_state(filename)

        with self.assertRaises(PermissionError):
            self.bridge.write_worker_state(filename, {"some": "data"})

    def test_sandbox_memory_bridge_injection_blocked(self):
        # Attempt write with code injection pattern
        filename = "malicious.json"
        unsafe_payload = {"command": "import os; os.system('echo hacked')"}
        with self.assertRaises(SecurityError):
            self.bridge.write_worker_state(filename, unsafe_payload)

    # === Telemetry Refresher Tests ===

    @patch("api.server.broadcast_system_alert")
    def test_telemetry_refresher_loop(self, mock_alert):
        mock_orch = MagicMock()
        mock_orch.get_cluster_snapshot.return_value = {
            "routing_state": "edge_preferred",
            "nodes": {
                "192.168.1.10": {"healthy": True, "drop_rate": 0.01},
                "192.168.1.11": {"healthy": False, "drop_rate": 0.12}
            }
        }
        mock_classifier = MagicMock()
        mock_classifier.classify.return_value = {
            "prediction": "spindle_chatter_detected",
            "confidence": 0.88,
            "class_probabilities": {"nominal": 0.12, "chatter": 0.88}
        }
        
        refresher = TelemetryRefresher(orchestrator=mock_orch, classifier=mock_classifier)
        
        # Test start/stop
        refresher.start()
        self.assertTrue(refresher._running)
        self.assertIsNotNone(refresher._thread)
        
        # Let loop run once
        time.sleep(0.25)
        
        refresher.stop()
        self.assertFalse(refresher._running)
        self.assertIsNone(refresher._thread)
        
        # Assert that broadcast_system_alert was called
        self.assertTrue(mock_alert.called)

if __name__ == "__main__":
    unittest.main()
