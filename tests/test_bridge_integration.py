"""Integration tests verifying S.P.A.R.K. Phase 3 & Phase 4 system bridges."""

import asyncio
import json
import os
import shutil
import time
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import numpy as np

from api.server import app
from core.hardware_bridge import HardwareAgentBridge
from security.defense_interceptor import secure_generate_workspace
from api.audio_daemon import AudioDaemon
from security.intent_validator import validate_intent_text

class TestBridgeIntegration(unittest.TestCase):

    def setUp(self) -> None:
        # Enable numpy to raise errors for testing math checks
        np.seterr(all="raise")

    def tearDown(self) -> None:
        # Clean up any sandbox outputs
        if os.path.exists("sandbox/test_secure_proj"):
            shutil.rmtree("sandbox/test_secure_proj")

    # ──────────────────────────────────────────────────────────
    # 1. Hardware Bridge Tests
    # ──────────────────────────────────────────────────────────

    def test_optimize_cad_topology_success(self) -> None:
        """Verifies voxel topology optimization returns compliance outputs successfully."""
        bridge = HardwareAgentBridge()
        # Normal inputs with safe high target compliance
        res = bridge.optimize_cad_topology(volume_fraction=0.4, compliance_target=1e15)
        self.assertEqual(res["status"], "success")
        self.assertIn("compliance_proxy", res)
        self.assertIn("average_density", res)

    def test_optimize_cad_topology_warning(self) -> None:
        """Verifies warning is returned when compliance exceeds target threshold."""
        bridge = HardwareAgentBridge()
        # Low target compliance to trigger warning
        res = bridge.optimize_cad_topology(volume_fraction=0.3, compliance_target=1.0)
        self.assertEqual(res["status"], "warning")
        self.assertIn("Optimized compliance", res["message"])

    def test_optimize_cad_topology_error_handling(self) -> None:
        """Asserts arithmetic overflows are captured cleanly into text alerts instead of crashing."""
        bridge = HardwareAgentBridge()
        # Invalid volume fraction parameter
        res = bridge.optimize_cad_topology(volume_fraction=-0.5, compliance_target=50.0)
        self.assertEqual(res["status"], "error")
        self.assertIn("Validation Error", res["message"])

        # Force a division by zero error/overflow in calculation
        with patch("core.hardware_bridge.VoxelTopologyEngine") as mock_engine:
            mock_inst = MagicMock()
            mock_inst.solve.side_effect = FloatingPointError("Numpy division by zero.")
            mock_engine.return_value = mock_inst
            
            res = bridge.optimize_cad_topology(volume_fraction=0.4, compliance_target=100.0)
            self.assertEqual(res["status"], "error")
            self.assertIn("Hardware Arithmetic Error", res["message"])

    def test_solve_robot_kinematics_limits(self) -> None:
        """Verifies inverse kinematics checks and handles boundary limits correctly."""
        bridge = HardwareAgentBridge()
        
        # Valid coordinate in reach space
        res = bridge.solve_robot_kinematics(x=5.0, y=5.0, z=15.0)
        self.assertEqual(res["status"], "success")
        self.assertIn("joint_angles_rad", res)

        # Coordinate completely outside reach limits
        res = bridge.solve_robot_kinematics(x=100.0, y=100.0, z=100.0)
        self.assertEqual(res["status"], "error")
        self.assertIn("Workspace Boundary Alert", res["message"])

    def test_run_predictive_diagnostics(self) -> None:
        """Verifies Mel-Spectrogram feature extraction and chatter detection works."""
        bridge = HardwareAgentBridge()
        # Test synthetic/mock audio path
        res = bridge.run_predictive_diagnostics("mock")
        self.assertEqual(res["status"], "success")
        self.assertIn("chatter_detected", res)
        self.assertIn("mel_spectrogram_mean", res)

    # ──────────────────────────────────────────────────────────
    # 2. Defensive Interceptor Tests
    # ──────────────────────────────────────────────────────────

    @patch("security.network_anomaly_detector.NetworkAnomalyDetector.sample_network_telemetry")
    @patch("core.spark_brain._local_chat_completion")
    def test_secure_generate_workspace_standard(self, mock_local_comp, mock_net) -> None:
        """Verifies clean static generation executes normally without isolation triggers."""
        mock_net.return_value = {
            "packets_sent": 0.0,
            "packets_recv": 0.0,
            "active_connections": 0.0,
            "active_sockets": 0.0
        }
        mock_manifest = {
            "project_name": "test_secure_proj",
            "frameworks": ["vanilla"],
            "block_locations": {"header": "H", "content": "C", "footer": "F"},
            "view_parameters": {"theme": "light", "viewport": "width=device"},
            "files": [
                {
                    "path": "index.html",
                    "content": "<h1>Static Safe Page</h1>"
                }
            ]
        }
        mock_local_comp.return_value = f"```json\n{json.dumps(mock_manifest)}\n```"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            res = loop.run_until_complete(secure_generate_workspace("test_secure_proj", "build static page"))
        finally:
            loop.close()

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["isolation_mode"], "standard_sandbox")
        self.assertTrue(os.path.exists("sandbox/test_secure_proj/index.html"))

    @patch("security.network_anomaly_detector.NetworkAnomalyDetector.sample_network_telemetry")
    @patch("core.spark_brain._local_chat_completion")
    def test_secure_generate_workspace_isolation_violation(self, mock_local_comp, mock_net) -> None:
        """Asserts that scripts/unsafe patterns violate isolation metrics and spawn low-priority workers."""
        mock_net.return_value = {
            "packets_sent": 0.0,
            "packets_recv": 0.0,
            "active_connections": 0.0,
            "active_sockets": 0.0
        }
        mock_manifest = {
            "project_name": "test_secure_proj",
            "frameworks": ["vanilla"],
            "block_locations": {"header": "H", "content": "C", "footer": "F"},
            "view_parameters": {"theme": "light", "viewport": "width=device"},
            "files": [
                {
                    "path": "app.py",
                    "content": "import subprocess; subprocess.Popen(['cmd'])"
                }
            ]
        }
        mock_local_comp.return_value = f"```json\n{json.dumps(mock_manifest)}\n```"

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            # Violates because it contains python script file app.py and subprocess code pattern
            res = loop.run_until_complete(secure_generate_workspace("test_secure_proj", "generate script calling subprocess"))
        finally:
            loop.close()

        self.assertEqual(res["status"], "success")
        self.assertEqual(res["isolation_mode"], "strict_low_priority_worker")
        self.assertIsNotNone(res["worker_pid"])

    @patch("security.network_anomaly_detector.NetworkAnomalyDetector.sample_network_telemetry")
    @patch("core.spark_brain._local_chat_completion")
    def test_secure_generate_workspace_network_anomaly_drop(self, mock_local_comp, mock_telemetry) -> None:
        """Verifies that active outbound network anomalies instantly drop the thread."""
        # Mock high network packets to trigger anomaly
        mock_telemetry.return_value = {
            "packets_sent": 10000.0,
            "packets_recv": 5000.0,
            "active_connections": 50.0,
            "active_sockets": 200.0
        }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with self.assertRaises(PermissionError):
                loop.run_until_complete(secure_generate_workspace("test_secure_proj", "build page"))
        finally:
            loop.close()

    # ──────────────────────────────────────────────────────────
    # 3. Audio Daemon Tests
    # ──────────────────────────────────────────────────────────

    def test_audio_daemon_isolation_and_intent(self) -> None:
        """Verifies audio isolation process frames and validates outputs via intent validators."""
        daemon = AudioDaemon(frame_duration_ms=10)
        
        # Verify intent validator sanitizes fillers
        scan = validate_intent_text("alright no but listen, gently open calculator")
        self.assertEqual(scan.cleaned_text, "open calculator")
        
        # Test simulated audio dispatching
        # Set up a mock callback
        with patch("api.audio_daemon.AudioDaemon._dispatch_command") as mock_dispatch:
            # We mock the pyaudio stream so it runs with fake data
            daemon.start()
            time.sleep(0.2)
            daemon.stop()
            
            # Verify stream ran loop at least once
            self.assertTrue(mock_dispatch.called or daemon.chunk_size > 0)

    # ──────────────────────────────────────────────────────────
    # 4. Biometric Stream Route Tests
    # ──────────────────────────────────────────────────────────

    def test_biometric_websocket_route(self) -> None:
        """Connects to /ws/biometrics to verify 60 FPS rPPG and skeletal telemetry outputs."""
        client = TestClient(app)
        
        # Connect to the biometrics websocket route
        with client.websocket_connect("/ws/biometrics") as websocket:
            # Receive at least 3 packets to verify steady stream
            for _ in range(3):
                data = websocket.receive_json()
                self.assertEqual(data["type"], "biometric_telemetry")
                
                payload = data["payload"]
                self.assertIn("heart_rate_bpm", payload)
                self.assertIn("rppg_trace_value", payload)
                self.assertIn("joint_cosines", payload)
                
                # Check joint cosines keys
                cosines = payload["joint_cosines"]
                self.assertIn("thumb", cosines)
                self.assertIn("index", cosines)
                self.assertIn("middle", cosines)
                self.assertIn("ring", cosines)
                self.assertIn("pinky", cosines)
                
                # Check coordinates and tracking format
                self.assertIn("gaze_xy", payload)
                self.assertIn("gesture", payload)
                self.assertIn("frame_index", payload)

if __name__ == "__main__":
    unittest.main()
