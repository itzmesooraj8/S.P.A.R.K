"""
S.P.A.R.K Advanced Hardware & Biometrics Test Suite
Validates FastICA separation, NLMS AEC, SLAM meshing, Farneback optical flows,
rPPG Butterworth filters, skeletal joint kinematics, and 1D CNN vibration classifications.
"""

import os
import shutil
import unittest
import numpy as np
from typing import Dict, List, Any

# Import targets under test
from core.audio_isolation import AcousticEchoCanceller, FastICASeparator, SpeakerDiarizationWrapper
from core.spatial_synthesis import TSDFMeshBuilder, VolumetricFluidFlow, OcclusionTracker
from core.human_telemetry import rPPGEngine, ThermalAffineMapper, ExpressionProfiler
from core.hand_eye_tracker import HandKinematicsTracker, PupilGazeAligner
from core.industrial_diagnostics import FEAIntegrationRunner, Vibration1DCNN

class SparkAdvancedHardwareTests(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = os.path.abspath("test_advanced_sandbox")
        os.makedirs(self.test_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # --- Layer 1 Tests: Acoustics ---
    def test_acoustic_echo_cancellation_nlms(self):
        aec = AcousticEchoCanceller(filter_length=32, step_size=0.05)
        # Create reference signal (e.g. white noise) and mixed microphone signal containing echo
        np.random.seed(42)
        ref = np.random.randn(500)
        # Construct true echo path: shift reference by 2 indices and scale
        true_echo = np.roll(ref, 2) * 0.5
        true_echo[:2] = 0.0
        
        # Mic signal contains voice + echo
        voice = np.sin(np.linspace(0, 10 * np.pi, 500)) * 0.1
        mic = voice + true_echo
        
        clean = aec.cancel_echo(ref, mic)
        
        # Verify echo reduction (error energy of second half should be lower than original mic energy)
        orig_energy = np.sum(mic[250:]**2)
        clean_energy = np.sum(clean[250:]**2)
        self.assertLess(clean_energy, orig_energy)

    def test_blind_source_separation_fastica(self):
        ica = FastICASeparator()
        np.random.seed(42)
        t_grid = np.linspace(0, 2.0, 1000)
        
        # Two independent sources: sine wave and random noise
        s1 = np.sin(2 * np.pi * 5 * t_grid)
        s2 = np.sign(np.sin(2 * np.pi * 3 * t_grid)) # square wave
        S = np.vstack((s1, s2))
        
        # Mix signals
        A = np.array([[0.6, 0.4], [0.3, 0.7]])
        X = A @ S
        
        separated = ica.separate_sources(X, max_iter=100)
        
        self.assertEqual(separated.shape, (2, 1000))
        # Correlation checks (each source should correlate highly with at least one separated component)
        c1 = max(abs(np.corrcoef(s1, separated[0])[0, 1]), abs(np.corrcoef(s1, separated[1])[0, 1]))
        c2 = max(abs(np.corrcoef(s2, separated[0])[0, 1]), abs(np.corrcoef(s2, separated[1])[0, 1]))
        
        self.assertGreater(c1, 0.8)
        self.assertGreater(c2, 0.8)
        
        # Diarization & Subvocal checks
        diarizer = SpeakerDiarizationWrapper()
        segs = diarizer.diarize_audio(s1)
        self.assertEqual(len(segs), 3)
        self.assertEqual(segs[0]["speaker_id"], "speaker_0")
        
        subvocal_cmd = diarizer.parse_subvocal_activity(np.ones(100) * 0.1)
        self.assertIn("SYSTEM_SHUTDOWN", subvocal_cmd)

    # --- Layer 2 Tests: Spatial ---
    def test_spatial_mesh_and_fluid_occlusions(self):
        # Mesh builder checks
        builder = TSDFMeshBuilder(voxel_size=0.01)
        depth = np.ones((100, 100)) * 1500.0 # 1.5m flat wall
        intrinsic = np.array([[500.0, 0, 50.0], [0, 500.0, 50.0], [0, 0, 1.0]])
        
        # Execute async integration
        import asyncio
        loop = asyncio.new_event_loop()
        verts, faces = loop.run_until_complete(builder.integrate_depth_frame(depth, intrinsic))
        loop.close()
        self.assertGreater(len(verts), 0)
        self.assertGreater(len(faces), 0)
        
        # Fluid flow checks
        flow_engine = VolumetricFluidFlow(use_farneback=False)
        frame1 = np.ones((50, 50), dtype=np.uint8) * 10
        frame2 = np.ones((50, 50), dtype=np.uint8) * 20
        flow = flow_engine.estimate_flow(frame1, frame2)
        self.assertEqual(flow.shape, (50, 50, 2))
        
        # Occlusion Tracker checks
        tracker = OcclusionTracker()
        # Move object along X-axis: 1.0 -> 2.0 -> 3.0
        tracker.update_positions({"drone_0": (1.0, 5.0, 2.0)})
        tracker.update_positions({"drone_0": (2.0, 5.0, 2.0)})
        
        pred = tracker.predict_occluded_object("drone_0", dt_seconds=1.0)
        # Expected position x = 2.0 + (1.0/dt)*1.0 = 2.0 + dx
        self.assertGreater(pred[0], 2.0)
        self.assertTrue(tracker.tracked_objects["drone_0"]["occluded"])

    # --- Layer 3 Tests: Human Telemetry ---
    def test_contactless_rppg_and_thermal(self):
        # rPPG Filter & FFT check
        fs = 30.0
        engine = rPPGEngine(sample_rate_fs=fs)
        
        # Create synthetic heart rate signal: 1.5 Hz (90 BPM) sine wave + noise
        t_grid = np.arange(0, 10, 1/fs)
        heart_freq = 1.5
        signal = np.sin(2.0 * np.pi * heart_freq * t_grid) + 0.1 * np.random.randn(len(t_grid))
        
        # Filter signal
        filtered = engine.butterworth_bandpass(signal, lowcut=0.75, highcut=3.3, order=4)
        bpm = engine.calculate_heart_rate(filtered)
        self.assertAlmostEqual(bpm, 90.0, delta=2.0)
        
        # Extract intensity checks
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        frame[:, :, 1] = 120 # Green Channel
        corners = np.array([[10, 10], [50, 10], [50, 50], [10, 50]])
        val = engine.extract_roi_intensity(frame, corners)
        self.assertEqual(val, 120.0)
        
        # Thermal overlay checks
        thermal = np.ones((50, 50), dtype=np.float32) * 36.5
        affine_mat = np.array([[1.0, 0.0, 5.0], [0.0, 1.0, 10.0], [0.0, 0.0, 1.0]])
        warped = ThermalAffineMapper.warp_thermal_overlay(thermal, affine_mat, (50, 50))
        self.assertEqual(warped.shape, (50, 50))
        
        # Expression Profiler check
        profiler = ExpressionProfiler()
        self.assertEqual(profiler.classify_expression(1.0, 0.2), "Focused")
        self.assertEqual(profiler.classify_expression(1.0, 2.0), "Fatigued (Yawning)")

    # --- Layer 4 Tests: Interactions ---
    def test_skeletal_hands_and_pupil_gaze(self):
        tracker = HandKinematicsTracker()
        
        # Test joint angles (right angle bones)
        base = np.array([0, 0, 0])
        mid = np.array([1, 0, 0])
        tip = np.array([1, 1, 0])
        angle = tracker.calculate_joint_angle(base, mid, tip)
        self.assertAlmostEqual(angle, np.pi/2.0)
        
        # Test squeeze gestures
        hand_open = np.zeros((21, 3))
        hand_open[[4, 8, 12, 16, 20]] = 1.0 # set fingertips far from wrist (0.0)
        hand_closed = np.ones((21, 3)) * 0.01 # compressed near wrist
        
        self.assertEqual(tracker.evaluate_gesture(hand_closed), "SQUEEZE")
        self.assertEqual(tracker.evaluate_gesture(hand_open), "NONE")
        
        # Pupil Gaze alignment checks
        aligner = PupilGazeAligner(screen_resolution=(1920, 1080))
        x_screen, y_screen = aligner.map_gaze_to_screen((0.1, 0.05), (0.0, 0.0))
        self.assertTrue(0 <= x_screen <= 1920)
        self.assertTrue(0 <= y_screen <= 1080)

    # --- Layer 5 Tests: Industrial Diagnostics ---
    def test_industrial_fea_and_1d_cnn(self):
        # FEA CalculiX process check
        runner = FEAIntegrationRunner(solver_path="calculix")
        # Dummy file trigger
        dummy_inp = os.path.join(self.test_dir, "test_job.inp")
        with open(dummy_inp, "w") as f:
            f.write("*HEADING\n*NODE\n")
            
        res = runner.run_mesh_fea(dummy_inp)
        self.assertTrue(res["success"])
        self.assertGreater(res["max_stress_mpa"], 0.0)
        
        # 1D CNN Classifier check
        cnn = Vibration1DCNN()
        # Input shape (3 channels, 50 timestamps) representing x,y,z vibration readings
        np.random.seed(42)
        imu_signal = np.random.randn(3, 50)
        
        pred_res = cnn.classify_vibration(imu_signal)
        self.assertIn("prediction", pred_res)
        self.assertIn(pred_res["prediction"], ["nominal", "bearing_deterioration", "axis_eccentricity"])
        self.assertTrue(0.0 <= pred_res["confidence"] <= 1.0)

if __name__ == "__main__":
    unittest.main()
