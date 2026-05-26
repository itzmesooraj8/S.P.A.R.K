"""
S.P.A.R.K Phase 3 Complete Defensive Operations & OS Control Test Suite
Validates visual GUI state hashing, supervisors, isolated browsers, anomalies, sandboxes,
self-healing, log compression, DB partitioning, ARP topology mappings, and edge resiliences.
"""

import os
import sys
import json
import shutil
import sqlite3
import unittest
from datetime import datetime
from unittest.mock import patch, MagicMock
from PIL import Image

# Import under test
from core.safe_gui import SafeGUIPipeline
from core.orchestrator.supervisor import WorkerSupervisor
from tools.isolated_browser import IsolatedBrowserInstance
from security.network_anomaly_detector import NetworkAnomalyDetector
from security.sandbox_wrapper import SandboxWrapper
from security.self_healing import SelfHealingDaemon
from core.vector_indexer import DocumentChunker, VectorKnowledgeIndexer
from core.log_synthesis import LogSynthesizer
from core.db_partitioner import DatabasePartitioner
from tools.topology_mapper import LocalTopologyMapper
from core.edge_resilience import EdgeResilienceManager

class SparkPhase3DefenseTests(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = os.path.abspath("test_sandbox_env")
        os.makedirs(self.test_dir, exist_ok=True)
        
    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
            
    # --- Module 1 Tests ---
    def test_safe_gui_hashing_and_verification(self):
        pipeline = SafeGUIPipeline(use_simulation=True)
        img = pipeline.capture_screen()
        self.assertIsInstance(img, Image.Image)
        
        # Test hash matching
        state_hash = pipeline.compute_state_hash(img)
        self.assertTrue(len(state_hash) == 64)
        
        success, actual_hash, token = pipeline.verify_and_click(
            x=100, y=200, 
            expected_pre_hash=pipeline.compute_state_hash(img)
        )
        self.assertTrue(success)
        self.assertEqual(len(token), 64)
        
        # Test typing
        type_success, _ = pipeline.verify_and_type("Hello World")
        self.assertTrue(type_success)

    def test_worker_supervisor_context_isolation(self):
        supervisor = WorkerSupervisor(workspace_dir=self.test_dir)
        
        # Test session context switching
        supervisor.switch_context("session_alpha")
        supervisor.add_history("user", "Hello Worker")
        supervisor.add_history("assistant", "Hello User")
        
        supervisor.switch_context("session_beta")
        supervisor.add_history("user", "Hello Sandbox")
        
        # Verify isolation
        alpha_hist = supervisor.get_history("session_alpha")
        beta_hist = supervisor.get_history("session_beta")
        
        self.assertEqual(len(alpha_hist), 2)
        self.assertEqual(len(beta_hist), 1)
        self.assertEqual(alpha_hist[0]["content"], "Hello Worker")
        self.assertEqual(beta_hist[0]["content"], "Hello Sandbox")
        
        # Test fork worker mock
        dummy_script = os.path.join(self.test_dir, "worker_dummy.py")
        with open(dummy_script, "w") as f:
            f.write("import sys; sys.exit(0)")
            
        proc = supervisor.fork_worker("dummy", "worker_dummy.py")
        self.assertIsNotNone(proc)
        proc.wait()
        
        status = supervisor.get_worker_status("dummy")
        self.assertIn("exited_with_", status)
        supervisor.terminate_worker("dummy")

    def test_isolated_browser_origin_check(self):
        # Whitelisted origin
        browser = IsolatedBrowserInstance(
            allowed_origins=["github.com", "google.com"],
            use_simulation=True
        )
        browser.start()
        
        # In origin set
        res_ok = browser.browse_url("https://github.com/login")
        self.assertTrue(res_ok["success"])
        
        # Blocked origin
        res_blocked = browser.browse_url("https://malicious-site.net/attack")
        self.assertFalse(res_blocked["success"])
        self.assertIn("SECURITY_BLOCKED", res_blocked["error"])
        browser.close()

    # --- Module 2 Tests ---
    def test_network_anomaly_evaluator(self):
        # Bus mock
        mock_bus = MagicMock()
        detector = NetworkAnomalyDetector(sample_interval=0.1, bus=mock_bus)
        
        # Sample normal metrics
        normal_metrics = {
            "packets_sent": 5.0,
            "packets_recv": 5.0,
            "active_connections": 2.0,
            "active_sockets": 10.0
        }
        
        detector.evaluate_metrics(normal_metrics)
        self.assertEqual(len(detector.anomaly_history), 0)
        
        # Sample anomalous metrics
        anomaly_metrics = {
            "packets_sent": 5000.0,
            "packets_recv": 6000.0,
            "active_connections": 300.0,
            "active_sockets": 1000.0
        }
        detector.evaluate_metrics(anomaly_metrics)
        self.assertEqual(len(detector.anomaly_history), 1)
        mock_bus.emit.assert_called_once()

    def test_sandbox_subprocess_wrapper_limits(self):
        wrapper = SandboxWrapper(memory_limit_mb=64, cpu_quota=0.1)
        
        # Test basic run
        code = "print('hello from sandbox')"
        success, stdout, stderr = wrapper.execute_in_sandbox(code)
        self.assertTrue(success, f"Subprocess sandbox execution failed: {stderr}")
        self.assertIn("hello from sandbox", stdout)
        
        # Test memory breach watchdog kill
        strict_wrapper = SandboxWrapper(memory_limit_mb=4, cpu_quota=0.1)
        heavy_code = """
import time
# Allocate massive array to trigger memory limits
try:
    arr = [0] * (5 * 1024 * 1024)
    time.sleep(2)
except Exception as e:
    print(e)
"""
        success_heavy, stdout_heavy, stderr_heavy = strict_wrapper.execute_in_sandbox(heavy_code, timeout=5)
        self.assertFalse(success_heavy)
        self.assertIn("KILLED_BY_SANDBOX", stderr_heavy)

    def test_self_healing_config_restoration(self):
        # Setup source config and initial state
        config_path = os.path.join(self.test_dir, "config.json")
        with open(config_path, "w") as f:
            f.write('{"status": "clean_config"}')
            
        daemon = SelfHealingDaemon(
            monitored_files=["config.json"],
            backup_dir="backup_domain",
            workspace_dir=self.test_dir
        )
        
        # Tamper the file
        with open(config_path, "w") as f:
            f.write('{"status": "TAMPERED_CONFIG"}')
            
        # Scan and verify auto restoration
        healed = daemon.scan_and_heal()
        self.assertIn("config.json", healed)
        
        with open(config_path, "r") as f:
            content = f.read()
        self.assertEqual(content, '{"status": "clean_config"}')

    # --- Module 3 Tests ---
    def test_document_chunker_and_indexing(self):
        text = "word " * 600 # 600 words
        chunks = DocumentChunker.chunk_text(text, chunk_size=100, chunk_overlap=10)
        self.assertGreater(len(chunks), 1)
        
        # Mock indexer integration
        indexer = VectorKnowledgeIndexer(db_path=os.path.join(self.test_dir, "mock_chroma"))
        dummy_doc = os.path.join(self.test_dir, "kb_doc.txt")
        with open(dummy_doc, "w") as f:
            f.write(text)
            
        chunk_count = indexer.index_file(dummy_doc, chunk_size=100, chunk_overlap=10)
        self.assertEqual(chunk_count, len(chunks))

    def test_log_synthesizer_de_noiser(self):
        synthesizer = LogSynthesizer()
        raw_logs = [
            "2026-05-26 12:00:00 - HEARTBEAT - core ping response ok",
            "2026-05-26 12:00:05 - HEARTBEAT - core ping response ok",
            "2026-05-26 12:00:10 - HEARTBEAT - core ping response ok",
            "2026-05-26 12:00:15 - DATABASE - chromadb insert complete",
            "2026-05-26 12:00:20 - GUI - pyautogui click coordinate 250,300",
        ]
        
        compressed_json = synthesizer.synthesize_stream(raw_logs)
        data = json.loads(compressed_json)
        
        self.assertEqual(len(data), 3) # collapsed heartbeat, db_query, gui_action
        self.assertEqual(data[0]["raw_occurrences"], 3)
        self.assertEqual(data[1]["raw_occurrences"], 1)
        
        agg = synthesizer.get_high_density_summary()
        self.assertEqual(agg["total_raw_processed"], 5)

    def test_db_partitioner_monthly_splits(self):
        partitioner = DatabasePartitioner(partition_dir=os.path.join(self.test_dir, "db_partitions"))
        
        # Log states and tool execution records
        partitioner.log_agent_state("researcher", "crawling", '{"active_tab": 1}')
        partitioner.log_runtime_event("INFO", "process_fork", "Spawning crawler worker")
        partitioner.log_tool_execution("web_search", '{"q": "spark"}', "results_success")
        
        # Verify db file is created
        db_files = os.listdir(partitioner.partition_dir)
        self.assertGreater(len(db_files), 0)
        self.assertTrue(db_files[0].endswith(".db"))
        
        # Query partition
        now = datetime.now()
        current_partition_date = f"{now.year}-{now.month:02d}"
        
        records = partitioner.query_cross_partitions("tool_execution_registry", current_partition_date, current_partition_date)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["tool_name"], "web_search")
        partitioner.close()

    # --- Module 4 Tests ---
    def test_local_topology_mapper(self):
        mapper = LocalTopologyMapper()
        
        # Raw Win32 arp -a output mock
        mock_arp_output = """
Interface: 192.168.1.10 --- 0xb
  Internet Address      Physical Address      Type
  192.168.1.1           00-04-4b-aa-bb-cc     dynamic
  192.168.1.2           ff-ff-ff-ff-ff-ff     static
  192.168.1.15          00-11-22-33-44-55     dynamic
"""
        nodes = mapper.parse_arp_table(mock_arp_output)
        self.assertEqual(len(nodes), 3)
        
        # Check Jetson classification
        self.assertEqual(nodes[0]["role"], "auxiliary_jetson_node")
        self.assertEqual(nodes[0]["hardware_category"], "Nvidia Jetson Embedded")
        self.assertEqual(nodes[2]["role"], "standard_network_client")

    def test_edge_resilience_manager_failover(self):
        manager = EdgeResilienceManager(
            cloud_endpoint="https://mockapi.com",
            latency_threshold_seconds=0.5,
            packet_drop_threshold=0.25,
            sample_count=2
        )
        
        # Mock high latency / drop rate
        health_metrics_bad = {
            "average_latency_seconds": 1.2,
            "drop_rate": 0.5,
            "success_rate": 0.5
        }
        
        state = manager.evaluate_routing_transition(health_metrics_bad)
        self.assertEqual(state, "local_fallback")
        self.assertEqual(os.environ.get("LLM_BACKEND"), "ollama")
        
        # Mock good health metrics restore
        health_metrics_good = {
            "average_latency_seconds": 0.2,
            "drop_rate": 0.0,
            "success_rate": 1.0
        }
        
        state = manager.evaluate_routing_transition(health_metrics_good)
        self.assertEqual(state, "cloud_preferred")
        self.assertEqual(os.environ.get("LLM_BACKEND"), "auto")

if __name__ == "__main__":
    unittest.main()
