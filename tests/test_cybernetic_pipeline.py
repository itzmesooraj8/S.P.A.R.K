from __future__ import annotations

import asyncio
import time
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import numpy as np

from biometrics.audio_isolation import AcousticEchoCanceller, FastICASeparator, SomaticAudioIsolator
from biometrics.human_telemetry import BiometricTelemetryDaemon, telemetry_daemon
from core.cad_engine import VoxelTopologyEngine
from core.model_router import get_ollama_model
from core.spark_brain import TOOLS, GroqFallbackError, _call_tool, _chat_completion, _run_planner
from generative.mesh_slicer import MeshContourSlicer
from security.intent_validator import clean_conversational_filler, validate_intent_text
from spatial.hand_eye_tracker import SomaticSkeletalTracker


class CyberneticPipelineTests(unittest.TestCase):
    def test_intent_matrix_and_local_fallback_regression(self) -> None:
        raw = "alright no but look, open tool custom"
        cleaned = clean_conversational_filler(raw)
        scan = validate_intent_text(raw)

        self.assertEqual(cleaned, "open tool custom")
        self.assertTrue(scan.allowed)
        self.assertEqual(scan.cleaned_text, "open tool custom")

        self.assertEqual(get_ollama_model("not-a-whitelisted-model"), "qwen2.5:7b")

        async def fake_planner(goal: str, sync_llm, tool_executor, tool_names, stream_sink=None):
            local_reply = await asyncio.to_thread(sync_llm, "fallback request")
            return {"goal": goal, "reply": local_reply, "tool_names": tool_names, "stream_sink": stream_sink}

        local_chain_result = SimpleNamespace(
            success=True,
            model_used="qwen2.5:7b",
            attempts=["qwen2.5:7b"],
            text="local ollama chain reply",
        )

        with patch("core.spark_brain.spark_plan_and_execute", side_effect=fake_planner), \
             patch("core.spark_brain.local_chain_complete", return_value=local_chain_result) as mock_chain, \
             patch("core.spark_brain.token_counter.get_remaining_today", return_value=10_000), \
             patch("core.spark_brain._groq_cooldown_until", time.time() + 60):
            result = asyncio.run(_run_planner("open a local tool"))

        self.assertEqual(result["reply"], "local ollama chain reply")
        mock_chain.assert_called_once()

        with patch("core.spark_brain.token_counter.get_remaining_today", return_value=10_000), \
             patch("core.spark_brain._groq_cooldown_until", time.time() + 60):
            with self.assertRaises(GroqFallbackError):
                asyncio.run(_chat_completion([{"role": "user", "content": "hello"}]))

    def test_cad_topology_fea_and_mesh_clearance(self) -> None:
        engine = VoxelTopologyEngine(nelx=8, nely=4, nelz=2, volfrac=0.35, yield_strength_mpa=30.0)
        density = engine.optimize(iterations=2)
        self.assertEqual(density.shape, (2, 4, 8))

        vertices = np.array(
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [0.0, 0.0, 25.0],
                [1.0, 0.0, 25.0],
                [1.0, 1.0, 25.0],
            ],
            dtype=np.float64,
        )
        faces = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.int64)
        fea = engine.evaluate_mesh(vertices, faces, force_vector=(0.0, 0.0, 500.0))
        self.assertFalse(fea["passed"])
        self.assertGreater(fea["weak_spots_count"], 0)
        self.assertGreaterEqual(fea["max_stress_mpa"], fea["yield_strength_mpa"])

        slicer = MeshContourSlicer(layer_height=0.05, feed_rate=900.0, spindle_speed=4200.0)
        self.assertAlmostEqual(slicer.normalize_step(1.125, is_cnc=True), 1.15)
        self.assertAlmostEqual(slicer.normalize_step(1.25, is_cnc=False), 1.2)

        mesh_vertices = np.array(
            [
                [0.02, 0.02, 0.00],
                [1.07, 0.02, 0.00],
                [1.07, 1.07, 0.05],
                [0.02, 1.07, 0.05],
            ],
            dtype=np.float64,
        )
        mesh_faces = np.array([[0, 1, 2], [0, 2, 3]], dtype=np.int64)
        gcode = slicer.slice_mesh(mesh_vertices, mesh_faces)
        motion_lines = [line for line in gcode if line.startswith("G0 X") or line.startswith("G1 X")]
        self.assertTrue(any("X0.800" in line and "Y0.400" in line for line in motion_lines))
        self.assertTrue(any("X0.400" in line and "Y0.800" in line for line in motion_lines))

    def test_cybernetic_somatic_interfaces(self) -> None:
        isolator = SomaticAudioIsolator()
        mic = np.vstack(
            [
                np.sin(np.linspace(0.0, 2.0 * np.pi, 128)),
                np.sin(np.linspace(0.0, 2.0 * np.pi, 128)) + 0.15 * np.cos(np.linspace(0.0, 4.0 * np.pi, 128)),
            ]
        )
        reference = np.sin(np.linspace(0.0, 2.0 * np.pi, 128))
        result = isolator.isolate(mic, reference)
        self.assertEqual(result.separated_streams.shape[1], 128)
        self.assertTrue(result.command_tokens["allowed"])

        echo_canceller = AcousticEchoCanceller(filter_length=16, step_size=0.2)
        cleaned = echo_canceller.cancel_echo(reference, mic[1])
        self.assertEqual(cleaned.shape[0], 128)
        self.assertFalse(np.allclose(cleaned, mic[1]))

        separator = FastICASeparator()
        separated = separator.separate_sources(mic, max_iter=10)
        self.assertEqual(separated.shape[1], 128)

        daemon = BiometricTelemetryDaemon(sample_rate=30.0, trace_window=150)
        green_trace = 120.0 + 5.0 * np.sin(np.linspace(0.0, 2.0 * np.pi * 5.0, 150))
        sample_1 = daemon.record_trace(green_trace, 75.0)
        sample_2 = daemon.record_trace(green_trace, 75.0)
        self.assertAlmostEqual(sample_1.heart_rate_bpm, sample_2.heart_rate_bpm, places=6)
        self.assertAlmostEqual(sample_1.heart_rate_bpm, 75.0, delta=10.0)

        tracker = SomaticSkeletalTracker()

        class DummyThread:
            def __init__(self, target, daemon=True, name=None):
                self._target = target

            def start(self):
                self._target()

            def join(self, timeout=None):
                return None

        frame_calls = {"count": 0}

        def frame_source() -> np.ndarray:
            frame_calls["count"] += 1
            raise RuntimeError("actuator force frame out of bounds")

        with patch("spatial.hand_eye_tracker.threading.Thread", DummyThread), \
             patch("spatial.hand_eye_tracker.threading.Event.wait", side_effect=lambda self, timeout=None: setattr(tracker, "_running", False)), \
             patch("api.server.broadcast_system_alert") as mock_broadcast:
            tracker.start_stream(frame_source)

        self.assertGreater(frame_calls["count"], 0)
        self.assertTrue(mock_broadcast.called)
        payload = mock_broadcast.call_args.args[0]
        self.assertEqual(payload["source"], "somatic_skeleton")
        self.assertEqual(payload["type"], "tracking_error")

    def test_phase_five_tool_registration_smoke(self) -> None:
        expected = {
            "isolate_somatic_audio",
            "record_human_telemetry",
            "encode_somatic_layout",
            "synthesize_spatial_scene",
            "run_industrial_diagnostics",
        }
        registered = {tool["function"]["name"] for tool in TOOLS}
        self.assertTrue(expected.issubset(registered))

        async def run_tool() -> None:
            result = await _call_tool("record_human_telemetry", {"green_trace": [120.0, 121.0, 122.0, 123.0], "heart_rate_bpm": 75.0})
            self.assertEqual(result["status"], "success")
            self.assertEqual(result["trace_length"], 4)

        asyncio.run(run_tool())


if __name__ == "__main__":
    unittest.main()