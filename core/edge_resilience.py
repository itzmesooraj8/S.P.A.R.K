"""
S.P.A.R.K Cloud-to-Edge Shifting State Engine
Monitors API token endpoint response speeds and packet drop rates,
triggering failover switches that sever cloud dependencies and force local fallback inference.
"""

import os
import time
import httpx
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("SPARK_EDGE_RESILIENCE")

class EdgeResilienceManager:
    """Monitors connection health and toggles S.P.A.R.K's active inference routing state."""
    
    def __init__(
        self,
        cloud_endpoint: str = "https://api.groq.com",
        latency_threshold_seconds: float = 0.8,
        packet_drop_threshold: float = 0.25,
        sample_count: int = 4
    ):
        self.cloud_endpoint = cloud_endpoint
        self.latency_threshold_seconds = latency_threshold_seconds
        self.packet_drop_threshold = packet_drop_threshold
        self.sample_count = sample_count
        
        # State values: "cloud_preferred", "local_fallback"
        self.current_routing_state = "cloud_preferred"
        self.latency_history: list[float] = []

    def check_connection_health(self) -> Dict[str, Any]:
        """Measures API token endpoint latency and checks for connection drop levels."""
        latencies = []
        drops = 0
        
        # Establish connection client with low timeout
        with httpx.Client(timeout=1.5) as client:
            for _ in range(self.sample_count):
                start = time.time()
                try:
                    # Lightweight HEAD or GET check
                    res = client.get(self.cloud_endpoint)
                    elapsed = time.time() - start
                    if res.status_code >= 500:
                        drops += 1
                    else:
                        latencies.append(elapsed)
                except httpx.RequestError:
                    drops += 1
                    
        drop_rate = float(drops) / self.sample_count
        avg_latency = sum(latencies) / len(latencies) if latencies else 999.0
        
        self.latency_history.append(avg_latency)
        if len(self.latency_history) > 20:
            self.latency_history.pop(0)
            
        return {
            "average_latency_seconds": avg_latency,
            "drop_rate": drop_rate,
            "success_rate": 1.0 - drop_rate
        }

    def evaluate_routing_transition(self, health_metrics: Dict[str, Any]) -> str:
        """Determines if connection degradation warrants switching to local fallback networks."""
        latency = health_metrics["average_latency_seconds"]
        drop_rate = health_metrics["drop_rate"]
        
        old_state = self.current_routing_state
        
        # Transition criteria
        if latency > self.latency_threshold_seconds or drop_rate > self.packet_drop_threshold:
            self.current_routing_state = "local_fallback"
        else:
            self.current_routing_state = "cloud_preferred"
            
        if old_state != self.current_routing_state:
            logger.warning(
                f"CLOUD-TO-EDGE ROUTE SHIFT: Routing state changed '{old_state}' -> '{self.current_routing_state}'. "
                f"Metrics: Latency={latency:.2f}s, Drop={drop_rate * 100:.0f}%"
            )
            self._apply_routing_configurations()
            
        return self.current_routing_state

    def _apply_routing_configurations(self) -> None:
        """Applies local environment routing locks corresponding to current state."""
        if self.current_routing_state == "local_fallback":
            # Force environment parameters to bypass Groq calls and lock onto local Ollama
            os.environ["LLM_BACKEND"] = "ollama"
            logger.info("Local Resilience: Fallback routing configurations set (LLM_BACKEND=ollama).")
        else:
            # Re-enable standard auto-routing
            os.environ["LLM_BACKEND"] = "auto"
            logger.info("Local Resilience: Cloud preferred routing configurations set (LLM_BACKEND=auto).")
            
    def force_state(self, state: str) -> None:
        """Allows direct programmatic state overrides."""
        if state not in ("cloud_preferred", "local_fallback"):
            raise ValueError("Invalid state destination.")
        self.current_routing_state = state
        self._apply_routing_configurations()
