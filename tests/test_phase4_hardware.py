"""
S.P.A.R.K Phase 4 Complete Hardware & Generative Engineering Test Suite
Validates SIMP optimization, DH kinematics, slicing G-code compilation,
async telemetry parsing, PID calculations, spectrograms, and thermal fatigue trackers.
"""

import os
import sys
import shutil
import unittest
import asyncio
import numpy as np
from typing import Dict, List, Any

# Import targets under test
from core.cad_engine import SIMPOptimizer2D, CADFEAValidator, ToleranceCalibrator
from core.robotics_cnc import DHKinematicsSolver, CNCSlicerEngine, SafetyInterlockMonitor
from core.edge_telemetry import EdgeTelemetryParser, PowerBusSupervisor, PIDBalanceFilter, OTALoaderEngine
from core.predictive_diagnostics import AcousticAnomalyDetector, ThermalFatigueTracker, DegradationCalibrator

class SparkPhase4HardwareTests(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = os.path.abspath("test_phase4_sandbox")
        os.makedirs(self.test_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # --- Module 1 Tests ---
    def test_simp_optimization_and_fea(self):
        # Topology optimization check
        opt = SIMPOptimizer2D(nelx=10, nely=5, volfrac=0.4, penal=3.0)
        density_grid = opt.optimize(iterations=2)
        self.assertEqual(density_grid.shape, (5, 10))
        self.assertAlmostEqual(np.mean(density_grid), 0.4, places=2)
        
        # FEA validator check
        fea = CADFEAValidator(yield_strength_mpa=250.0)
        vertices = np.array([[0,0,0], [1,0,0], [1,1,0], [0,0,10]])
        faces = np.array([[0,1,2], [0,1,3]])
        res = fea.validate_mesh(vertices, faces, force_vector=(0.0, 100.0, 0.0))
        self.assertIn("max_stress_mpa", res)
        self.assertIn("passed", res)
        
        # Tolerance calibrator check
        cal = ToleranceCalibrator(nozzle_diameter=0.4, cnc_tolerance=0.05)
        adjusted_fdm = cal.adjust_clearance(1.0, is_cnc=False)
        self.assertAlmostEqual(adjusted_fdm, 1.2) # closest multiple of 0.4 is 1.2
        adjusted_cnc = cal.adjust_clearance(1.03, is_cnc=True)
        self.assertAlmostEqual(adjusted_cnc, 1.05) # closest multiple of 0.05 is 1.05

    # --- Module 2 Tests ---
    def test_robotics_kinematics_and_slicing(self):
        # Kinematics check
        lengths = (10.0, 8.0, 6.0)
        solver = DHKinematicsSolver(link_lengths=lengths)
        
        # Test FK -> IK -> FK loop
        target_angles = (0.5, 0.2, -0.4)
        x, y, z = solver.forward_kinematics(target_angles)
        self.assertTrue(isinstance(x, float))
        
        ik_angles = solver.inverse_kinematics((x, y, z))
        x_recon, y_recon, z_recon = solver.forward_kinematics(ik_angles)
        self.assertAlmostEqual(x, x_recon, places=3)
        self.assertAlmostEqual(y, y_recon, places=3)
        self.assertAlmostEqual(z, z_recon, places=3)
        
        # Out of bounds check
        with self.assertRaises(ValueError):
            solver.inverse_kinematics((999.0, 999.0, 999.0))
            
        # CNC slicer check
        slicer = CNCSlicerEngine(layer_height=0.5, feed_rate=1000.0)
        vertices_mesh = np.array([[0,0,0], [5,0,0], [0,5,0], [0,0,2]])
        faces_mesh = np.array([[0,1,2], [0,1,3]])
        gcode = slicer.slice_mesh(vertices_mesh, faces_mesh)
        self.assertGreater(len(gcode), 0)
        self.assertEqual(gcode[1], "G21 ; Set units to millimeters")
        
        # Safety Current Interlock check
        monitor = SafetyInterlockMonitor(current_ceiling_amps=3.0)
        halted = [False]
        def e_stop_callback():
            halted[0] = True
            
        # Below ceiling
        monitor.check_motor_current(2.5, e_stop_callback)
        self.assertFalse(halted[0])
        
        # Above ceiling
        monitor.check_motor_current(3.2, e_stop_callback)
        self.assertTrue(halted[0])

    # --- Module 3 Tests ---
    def test_edge_telemetry_bus_and_pid(self):
        # Parser check
        parser = EdgeTelemetryParser(use_simulation=True)
        
        packet_received = [False]
        def on_packet(data):
            packet_received[0] = True
            
        async def run_parser_test():
            # Run parser loop for a very short duration
            task = asyncio.create_task(parser.start_parsing(on_packet))
            await asyncio.sleep(0.2)
            parser.running = False
            await task
            
        asyncio.run(run_parser_test())
        self.assertTrue(packet_received[0])
        self.assertIn("imu_roll", parser.system_status)
        self.assertIn("load_power_w", parser.system_status)
        
        # Power bus monitoring check
        power_supervisor = PowerBusSupervisor(critical_voltage_threshold=10.5)
        profile_nom = power_supervisor.evaluate_bus_loads({"motor_voltage": 12.0, "motor_current": 1.0})
        self.assertEqual(profile_nom, "nominal_power_profile")
        
        profile_drop = power_supervisor.evaluate_bus_loads({"motor_voltage": 10.1, "motor_current": 1.0})
        self.assertEqual(profile_drop, "emergency_low_power_profile")
        
        profile_high = power_supervisor.evaluate_bus_loads({"motor_voltage": 12.0, "motor_current": 4.0})
        self.assertEqual(profile_high, "high_load_throttled_profile")
        
        # PID Filter check
        pid = PIDBalanceFilter(kp=1.0, ki=0.2, kd=0.05)
        out1 = pid.compute_stabilization_output(0.5, target_angle=0.0)
        self.assertTrue(isinstance(out1, float))
        
        # OTA loader check
        ota = OTALoaderEngine(target_ip="192.168.1.99")
        blob = ota.compile_firmware_blob({"baud": 9600})
        self.assertTrue(blob.startswith(b"ESPOTA_FIRMWARE_HEADER"))
        
        ok, msg = ota.flash_ota(blob)
        self.assertTrue(ok)
        self.assertIn("OTA_SUCCESS", msg)

    # --- Module 4 Tests ---
    def test_predictive_diagnostics_and_calibration(self):
        # Audio spectrogram check
        detector = AcousticAnomalyDetector(use_simulation=True)
        waveform = np.sin(np.linspace(0, 10, 4096))
        spec = detector.generate_spectrogram(waveform)
        self.assertEqual(spec.shape[0], 64) # n_mels = 64
        
        # Chatter check
        is_anom, conf = detector.detect_bearing_chatter(spec)
        self.assertFalse(is_anom)
        
        # Simulated spike energy
        spec_spike = np.ones((64, 10)) * 2.0
        is_anom_spike, conf_spike = detector.detect_bearing_chatter(spec_spike)
        self.assertTrue(is_anom_spike)
        
        # Thermal fatigue check
        fatigue_db = os.path.join(self.test_dir, "test_fatigue.db")
        tracker = ThermalFatigueTracker(db_path=fatigue_db)
        
        fatigue, replace_flag = tracker.log_operational_cycle("spindle_joint", temp=95.0, duration=100.0)
        self.assertFalse(replace_flag)
        self.assertGreater(fatigue, 0)
        
        # Stress thermal loop to trigger flag
        _, replace_flag_severe = tracker.log_operational_cycle("spindle_joint", temp=350.0, duration=8000.0)
        self.assertTrue(replace_flag_severe)
        
        # Post run calibration check
        calibrator = DegradationCalibrator(tolerance_threshold=0.02)
        expected = np.array([[10, 10, 10], [20, 20, 20]])
        # Inside tolerance bounds
        actual_good = np.array([[10.01, 9.99, 10.00], [20.00, 20.01, 19.99]])
        res_good = calibrator.evaluate_run(actual_good, expected)
        self.assertFalse(res_good["recalibration_required"])
        
        # Outside tolerance bounds
        actual_bad = np.array([[10.05, 9.92, 10.03], [20.06, 20.01, 19.91]])
        res_bad = calibrator.evaluate_run(actual_bad, expected)
        self.assertTrue(res_bad["recalibration_required"])
        self.assertGreater(len(res_bad["suggested_calibration_gcode"]), 0)

if __name__ == "__main__":
    unittest.main()
