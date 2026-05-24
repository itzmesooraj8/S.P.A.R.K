import unittest
from unittest.mock import MagicMock
import numpy as np
import cv2
import time

# Target imports
from core.perception.spatial_slam import AsyncSpatialSLAM
from core.perception.structural_integrity import OcclusionTracker
from core.perception.fluid_analysis import FluidSmokeAnalyzer
from core.perception.object_detector import ONNXObjectDetector
from core.perception.ballistic_trajectory import BallisticTrajectoryPredictor
from core.perception.spectral_matcher import ComponentSpectralMatcher
from core.perception.vital_signs import ContactlessRPPG
from core.perception.behavioral_profiler import BehavioralProfiler
from core.perception.toxicity_scanner import OpticalToxicityScanner
from core.perception.sensor_fusion import NetworkSensorStitcher, MultiSpectralLayerer
from core.perception.gesture_interface import HandSkeletonTracker, PhysicsHolographicController
from cognitive.knowledge_graph import LocalKnowledgeGraph
from cognitive.multimodal_grounding import MultimodalGrounder
from cognitive.load_regulator import CognitiveLoadRegulator

class TestPhase2Vision(unittest.TestCase):

    def test_spatial_slam_reconstruction(self):
        slam = AsyncSpatialSLAM()
        slam.start()
        
        # Ingest simulated flat depth map (10x10) to ensure rapid mesh creation
        rgb = np.random.randint(0, 255, size=(10, 10, 3), dtype=np.uint8)
        depth = np.full((10, 10), 1000, dtype=np.int16)
        intrinsic = np.array([
            [500.0, 0.0, 5.0],
            [0.0, 500.0, 5.0],
            [0.0, 0.0, 1.0]
        ])
        
        slam.add_depth_points(rgb, depth, intrinsic)
        
        # Let point cloud thread execute once
        time.sleep(0.6)
        slam.stop()
        
        # Point cloud should have voxel downsampled points
        self.assertGreater(len(slam.point_cloud.points), 0)
        self.assertIsInstance(slam.get_mesh_vertices_count(), int)

    def test_occlusion_tracker(self):
        tracker = OcclusionTracker()
        
        # Coordinate states
        pos_t0 = np.array([1.0, 2.0, 3.0])
        pos_t1 = np.array([1.1, 2.0, 3.0])
        
        # Step 0
        tracker.update({10: pos_t0})
        pos, occluded = tracker.get_object_position(10)
        self.assertFalse(occluded)
        self.assertTrue(np.array_equal(pos, pos_t0))
        
        # Step 1
        tracker.update({10: pos_t1})
        pos, occluded = tracker.get_object_position(10)
        self.assertFalse(occluded)
        
        # Step 2: Target is occluded (lost from camera detector)
        tracker.update({})
        pos, occluded = tracker.get_object_position(10)
        self.assertTrue(occluded)
        # Newtonian velocity estimation predicts trajectory
        self.assertGreater(pos[0], 1.1)

    def test_fluid_smoke_analysis(self):
        analyzer = FluidSmokeAnalyzer()
        
        # Frame 0
        frame_a = np.zeros((100, 100, 3), dtype=np.uint8)
        res_a = analyzer.analyze_frame(frame_a)
        self.assertEqual(res_a["smoke_index"], 0.0)
        
        # Frame 1: Introduce displacement
        frame_b = np.zeros((100, 100, 3), dtype=np.uint8)
        frame_b[10:90, 10:90, :] = 120
        res_b = analyzer.analyze_frame(frame_b)
        self.assertIn("smoke_index", res_b)
        self.assertIn("fluid_movement", res_b)

    def test_onnx_object_detector(self):
        detector = ONNXObjectDetector()
        frame = np.zeros((200, 400, 3), dtype=np.uint8)
        
        detections = detector.detect_and_track(frame)
        self.assertEqual(len(detections), 2)
        self.assertEqual(detections[0]["label"], "person")
        self.assertEqual(detections[1]["label"], "component")

    def test_ballistic_trajectory_predictor(self):
        predictor = BallisticTrajectoryPredictor(g=-9.8)
        
        # Register points along trajectory path
        predictor.register_position(1, np.array([0.0, 0.0, 0.0]), 0.0)
        predictor.register_position(1, np.array([1.0, 2.0, 0.0]), 0.1)
        predictor.register_position(1, np.array([2.0, 3.8, 0.0]), 0.2)
        
        # Predict 0.5s into the future
        prediction = predictor.predict_intercept(1, 0.5)
        self.assertIsInstance(prediction, np.ndarray)
        self.assertEqual(len(prediction), 3)
        self.assertLess(prediction[1], 10.0) # check physical gravity limits

    def test_component_spectral_matcher(self):
        matcher = ComponentSpectralMatcher()
        
        # Match RES_10K crop
        crop = np.zeros((20, 20, 3), dtype=np.uint8)
        crop[:, :] = [100, 50, 200]  # raw channel distributions
        
        name, similarity = matcher.match_component(crop)
        self.assertIn(name, matcher.catalog.keys())
        self.assertGreater(similarity, 0.0)

    def test_contactless_rppg(self):
        # Simulated PPG over 150 frames (30fps => 5 seconds)
        rppg = ContactlessRPPG(buffer_size=150, fps=30.0)
        
        # Heart rate freq: 1.25 Hz => 75 BPM
        t = np.linspace(0, 5.0, 150)
        pulse = 120 + 5.0 * np.sin(2 * np.pi * 1.25 * t)
        
        for p in pulse:
            roi = np.zeros((10, 10, 3), dtype=np.uint8)
            # R, G, B channels change with pulse
            roi[:, :, 1] = int(p)
            roi[:, :, 0] = int(120.0 + 3.0 * np.sin(2 * np.pi * 1.25 * t[0]))
            roi[:, :, 2] = int(120.0 + 3.0 * np.sin(2 * np.pi * 1.25 * t[0]))
            bpm = rppg.process_frame(roi)
            
        self.assertGreater(bpm, 60.0)
        self.assertLess(bpm, 90.0)

    def test_behavioral_profiler(self):
        profiler = BehavioralProfiler()
        
        # Face: brow landmarks
        face = np.zeros((115, 3))
        face[70] = [1.0, 1.0, 0.0]
        face[107] = [1.0, 1.2, 0.0] # distance = 0.2
        
        # Body: shoulders and hips
        body = np.zeros((26, 3))
        body[11] = [0.0, 1.0, 0.0]  # left shoulder
        body[12] = [1.0, 1.0, 0.0]  # right shoulder => mid-shoulder: [0.5, 1.0, 0.0]
        body[23] = [0.1, 0.0, 0.0]  # left hip
        body[24] = [0.9, 0.0, 0.0]  # right hip => mid-hip: [0.5, 0.0, 0.0] => horizontal offset = 0.0
        
        metrics = profiler.evaluate_pose(face, body)
        self.assertIn("micro_expression_stress", metrics)
        self.assertIn("gait_imbalance", metrics)
        self.assertEqual(metrics["gait_imbalance"], 0.0)

    def test_optical_toxicity_scanner(self):
        scanner = OpticalToxicityScanner()
        
        # Neutral image
        neutral = np.full((10, 10, 3), 100, dtype=np.uint8)
        val_neutral = scanner.evaluate_chromatic_shift(neutral)
        self.assertEqual(val_neutral, 0.0)

        # Decay yellowing image (high Red/Green, low Blue)
        decay = np.zeros((10, 10, 3), dtype=np.uint8)
        decay[:, :, 2] = 220  # Red
        decay[:, :, 1] = 200  # Green
        decay[:, :, 0] = 20   # Blue
        val_decay = scanner.evaluate_chromatic_shift(decay)
        self.assertGreater(val_decay, 0.5)

    def test_sensor_stitching_and_layering(self):
        stitcher = NetworkSensorStitcher()
        
        src_pts = np.array([[0,0], [10,0], [10,10], [0,10]], dtype=np.float32)
        dst_pts = np.array([[5,5], [15,5], [15,15], [5,15]], dtype=np.float32)
        stitcher.register_node(1, src_pts, dst_pts)
        
        frame = np.full((20, 20, 3), 100, dtype=np.uint8)
        stitched = stitcher.warp_and_stitch({1: frame}, (30, 30))
        self.assertEqual(stitched.shape, (30, 30, 3))
        
        # Test MultiSpectralLayerer
        layerer = MultiSpectralLayerer()
        rgb = np.full((100, 100, 3), 50, dtype=np.uint8)
        thermal = np.full((100, 100, 3), 10, dtype=np.uint8)
        thermal[10:30, 10:30, :] = 200 # thermal hot signature
        
        fused = layerer.fuse_spectral_feeds(rgb, thermal)
        self.assertEqual(fused.shape, rgb.shape)
        # Verify de-noising outputs are color matrices
        self.assertEqual(len(fused.shape), 3)

    def test_gesture_interface_hand_and_eye(self):
        tracker = HandSkeletonTracker()
        
        # Joint array
        joints = np.zeros((21, 3))
        joints[4] = [0.1, 0.2, 0.3] # thumb tip
        joints[8] = [0.1, 0.21, 0.3] # index tip => distance = 0.01 (pinch!)
        
        hand_info = tracker.parse_joints(joints)
        self.assertEqual(hand_info["gesture"], "pinch_select")
        self.assertLess(hand_info["pinch_distance"], tracker.pinch_threshold)
        
        # Test PhysicsHolographicController
        controller = PhysicsHolographicController()
        controller.update_physics(np.array([10.0, 0.0]), dt=0.1)
        self.assertGreater(controller.position[0], 0.0)
        
        # Eye Gaze
        gaze = (12.0, 12.0)
        box = (0.0, 20.0, 0.0, 20.0) # center is (10, 10). Gaze is top-right => Quadrant 1
        q = controller.get_eye_quadrant(gaze, box)
        self.assertEqual(q, 1)

    def test_knowledge_graph(self):
        kg = LocalKnowledgeGraph()
        kg.add_relationship("brightness_cmd", "triggers", "brightness_control")
        
        conns = kg.get_connected_entities("brightness_cmd")
        self.assertEqual(len(conns), 1)
        self.assertEqual(conns[0]["target"], "brightness_control")
        self.assertEqual(conns[0]["relationship"], "triggers")

    def test_multimodal_grounding(self):
        grounder = MultimodalGrounder()
        
        # Case 1: Plain command
        plain = grounder.resolve_deictic_references("open file", 1)
        self.assertEqual(plain, "open file")
        
        # Case 2: Deictic markers
        resolved = grounder.resolve_deictic_references("open this", 3)
        self.assertIn("resolved target: sensor_telemetry_out.csv", resolved)

    def test_cognitive_load_regulation(self):
        regulator = CognitiveLoadRegulator(latency_threshold_ms=800.0)
        
        verbose = "The brightness on the primary monitor has been updated. Operational checks are successful."
        
        # Normal latency
        res_normal = regulator.regulate_response(verbose, 200.0, 10.0)
        self.assertEqual(res_normal, verbose)
        
        # High CPU stress
        res_choked = regulator.regulate_response(verbose, 200.0, 92.0)
        self.assertIn("[CHOKED ALERT] Status: OK.", res_choked)
        self.assertEqual(res_choked, "[CHOKED ALERT] Status: OK. The brightness on the primary monitor has been updated.")

if __name__ == "__main__":
    unittest.main()
