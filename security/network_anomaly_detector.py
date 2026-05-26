"""
S.P.A.R.K Heuristic Inbound/Outbound Network Anomaly Detection
Background sampler that tracks packet rates, active connections, and open sockets,
raising events when connection density or throughput exceeds statistical thresholds.
"""

import time
import logging
import threading
from typing import Dict, List, Any, Optional
import psutil

logger = logging.getLogger("SPARK_NETWORK_MONITOR")

class NetworkAnomalyDetector:
    """Monitors system network interfaces and flags deviations from standard load profiles."""
    
    def __init__(
        self, 
        sample_interval: float = 1.0, 
        max_deviation_multiplier: float = 3.0,
        bus: Optional[Any] = None
    ):
        self.sample_interval = sample_interval
        self.max_deviation_multiplier = max_deviation_multiplier
        self.bus = bus
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        
        # Baselines arrays [packets_sent, packets_recv, active_connections, active_sockets]
        self.baselines: List[float] = [10.0, 10.0, 5.0, 20.0]
        self.samples_collected = 0
        
        self.anomaly_history: List[Dict[str, Any]] = []

    def start(self) -> None:
        """Start the background monitoring thread."""
        if self.running:
            return
        self.running = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        logger.info("Network anomaly detector background thread launched.")

    def stop(self) -> None:
        """Stop the background monitoring thread."""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2.0)
        logger.info("Network anomaly detector background thread stopped.")

    def sample_network_telemetry(self) -> Dict[str, Any]:
        """Interrogates system telemetry interfaces for networking stats."""
        try:
            io_before = psutil.net_io_counters()
            time.sleep(0.1) # short delta to compute rate
            io_after = psutil.net_io_counters()
            
            packets_sent_rate = io_after.packets_sent - io_before.packets_sent
            packets_recv_rate = io_after.packets_recv - io_before.packets_recv
            
            # Connections count
            conns = psutil.net_connections(kind="inet")
            active_conns = len([c for c in conns if c.status == "ESTABLISHED"])
            active_sockets = len(conns)
            
            return {
                "packets_sent": float(packets_sent_rate * 10), # scale to per-second rate
                "packets_recv": float(packets_recv_rate * 10),
                "active_connections": float(active_conns),
                "active_sockets": float(active_sockets)
            }
        except Exception as e:
            logger.error(f"Failed to fetch network telemetry: {e}")
            return {"packets_sent": 0.0, "packets_recv": 0.0, "active_connections": 0.0, "active_sockets": 0.0}

    def _monitor_loop(self) -> None:
        """Continuous polling check evaluating running metrics against baselines."""
        while self.running:
            try:
                metrics = self.sample_network_telemetry()
                
                # Check for anomalies
                self.evaluate_metrics(metrics)
                
                # Adapt/update baselines dynamically for the first 100 loops
                if self.samples_collected < 100:
                    self._update_baselines(metrics)
                
                time.sleep(self.sample_interval)
            except Exception as e:
                logger.error(f"Error in anomaly loop: {e}")
                time.sleep(self.sample_interval)

    def evaluate_metrics(self, metrics: Dict[str, Any]) -> None:
        """Compare current telemetry metric snapshot to baseline thresholds."""
        keys = ["packets_sent", "packets_recv", "active_connections", "active_sockets"]
        anomalies_detected = []
        
        for idx, key in enumerate(keys):
            curr_val = metrics[key]
            baseline_val = self.baselines[idx]
            threshold = max(baseline_val * self.max_deviation_multiplier, baseline_val + 50.0)
            
            if curr_val > threshold:
                anomalies_detected.append({
                    "metric": key,
                    "baseline": baseline_val,
                    "current": curr_val,
                    "threshold": threshold
                })
        
        if anomalies_detected:
            # Anomaly trigger
            anomaly_payload = {
                "timestamp": time.time(),
                "severity": "CRITICAL" if len(anomalies_detected) > 1 else "MEDIUM",
                "details": anomalies_detected
            }
            self.anomaly_history.append(anomaly_payload)
            logger.warning(f"NETWORK ANOMALY DETECTED: {anomaly_payload}")
            
            # Emit to agent bus if present
            if self.bus:
                try:
                    self.bus.emit("security.network_anomaly", anomaly_payload)
                except Exception as e:
                    logger.debug(f"Failed to emit network anomaly event to bus: {e}")

    def _update_baselines(self, metrics: Dict[str, Any]) -> None:
        """Smooth baseline arrays dynamically over time using moving average calculation."""
        keys = ["packets_sent", "packets_recv", "active_connections", "active_sockets"]
        self.samples_collected += 1
        alpha = 0.1 # smooth factor
        for idx, key in enumerate(keys):
            self.baselines[idx] = (alpha * metrics[key]) + ((1 - alpha) * self.baselines[idx])
