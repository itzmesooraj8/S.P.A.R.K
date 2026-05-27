"""Phase 3 swarm orchestration and local edge discovery."""

from __future__ import annotations

import logging
import os
import re
import socket
import subprocess
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

import httpx

from core.edge_resilience import EdgeResilienceManager
from tools.topology_mapper import LocalTopologyMapper

logger = logging.getLogger("SPARK_SWARM_ORCHESTRATOR")


@dataclass(slots=True)
class ClusterNode:
    ip_address: str
    mac_address: str = ""
    role: str = "standard_network_client"
    hardware_category: str = "Generic Endpoint"
    hostname: str = ""
    latency_seconds: float = 999.0
    drop_rate: float = 1.0
    ollama_url: str = ""
    healthy: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class SwarmOrchestrator:
    """Discovers adjacent compute endpoints and shifts inference routing under stress."""

    def __init__(
        self,
        cloud_endpoint: str = "https://api.groq.com",
        ollama_port: int = 11434,
        discovery_interval_seconds: float = 5.0,
        health_interval_seconds: float = 0.5,
    ) -> None:
        self.cloud_endpoint = cloud_endpoint
        self.ollama_port = ollama_port
        self.discovery_interval_seconds = discovery_interval_seconds
        self.health_interval_seconds = health_interval_seconds
        self.topology_mapper = LocalTopologyMapper()
        self.edge_resilience = EdgeResilienceManager(cloud_endpoint=cloud_endpoint)
        self._lock = threading.RLock()
        self._running = False
        self._discovery_thread: Optional[threading.Thread] = None
        self._health_thread: Optional[threading.Thread] = None
        self._node_regex = re.compile(
            r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3}).*?(?P<mac>[0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5}).*?(?P<link>dynamic|static)?",
            re.IGNORECASE,
        )
        self.cluster_nodes: Dict[str, ClusterNode] = {}
        self.routing_state = "cloud_preferred"

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._discovery_thread = threading.Thread(target=self._discovery_loop, daemon=True, name="swarm-discovery")
        self._health_thread = threading.Thread(target=self._health_loop, daemon=True, name="swarm-health")
        self._discovery_thread.start()
        self._health_thread.start()

    def stop(self) -> None:
        self._running = False
        if self._discovery_thread:
            self._discovery_thread.join(timeout=2.0)
        if self._health_thread:
            self._health_thread.join(timeout=2.0)

    def _read_arp_table(self) -> str:
        try:
            if os.name == "nt":
                return subprocess.check_output(["arp", "-a"], text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            return subprocess.check_output(["arp", "-n"], text=True)
        except Exception as exc:
            logger.debug(f"ARP lookup failed: {exc}")
            return ""

    def _scan_nodes(self, raw_arp: str) -> list[dict[str, Any]]:
        if not raw_arp:
            return []

        nodes = self.topology_mapper.parse_arp_table(raw_arp)
        for line in raw_arp.splitlines():
            match = self._node_regex.search(line.strip())
            if not match:
                continue
            ip = match.group("ip")
            mac = match.group("mac")
            link = match.group("link") or "dynamic"
            nodes.append(self.topology_mapper._classify_node(ip, mac, link))
        return nodes

    def discover_local_nodes(self) -> Dict[str, ClusterNode]:
        raw_arp = self._read_arp_table()
        discovered: Dict[str, ClusterNode] = {}
        for node in self._scan_nodes(raw_arp):
            ip = node.get("ip_address", "")
            if not ip:
                continue
            discovered[ip] = ClusterNode(
                ip_address=ip,
                mac_address=node.get("mac_address", ""),
                role=node.get("role", "standard_network_client"),
                hardware_category=node.get("hardware_category", "Generic Endpoint"),
                hostname=node.get("hostname", ""),
                ollama_url=f"http://{ip}:{self.ollama_port}",
                metadata={"link_type": node.get("link_type", "dynamic")},
            )

        with self._lock:
            for ip, node in discovered.items():
                self.cluster_nodes[ip] = node
        return discovered

    def poll_node_latency(self, ip_address: str, timeout_seconds: float = 0.5) -> tuple[float, float, bool]:
        """Polls a node at 2 Hz using a socket connect and a lightweight Ollama HEAD check."""
        start = time.perf_counter()
        drops = 0
        healthy = False
        try:
            with socket.create_connection((ip_address, self.ollama_port), timeout=timeout_seconds):
                pass
            latency = time.perf_counter() - start
            try:
                with httpx.Client(timeout=timeout_seconds) as client:
                    response = client.get(f"http://{ip_address}:{self.ollama_port}/api/tags")
                    healthy = response.status_code < 500
                    if not healthy:
                        drops += 1
            except Exception:
                healthy = False
                drops += 1
        except Exception:
            latency = timeout_seconds * 2.0
            drops += 1

        drop_rate = 1.0 if drops else 0.0
        return latency, drop_rate, healthy

    def _shed_to_local_inference(self, node: ClusterNode) -> None:
        os.environ["LLM_BACKEND"] = "ollama"
        if node.ollama_url:
            os.environ["OLLAMA_HOST"] = node.ollama_url
        self.routing_state = "local_fallback"
        logger.warning(f"Swarm fallback engaged on {node.ip_address}; coordinating local Ollama inference.")

    def _restore_cloud_preference(self) -> None:
        os.environ["LLM_BACKEND"] = "auto"
        self.routing_state = "cloud_preferred"

    def evaluate_node_health(self, node: ClusterNode) -> ClusterNode:
        latency, drop_rate, healthy = self.poll_node_latency(node.ip_address)
        node.latency_seconds = latency
        node.drop_rate = drop_rate
        node.healthy = healthy and latency <= self.edge_resilience.latency_threshold_seconds and drop_rate <= self.edge_resilience.packet_drop_threshold
        if not node.healthy:
            self._shed_to_local_inference(node)
        return node

    def get_cluster_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "routing_state": self.routing_state,
                "node_count": len(self.cluster_nodes),
                "nodes": {ip: asdict(node) for ip, node in self.cluster_nodes.items()},
            }

    def route_inference(self, prompt: str) -> Dict[str, Any]:
        """Returns the preferred execution path for a prompt under current health conditions."""
        with self._lock:
            preferred = next((node for node in self.cluster_nodes.values() if node.healthy), None)
            if preferred:
                return {
                    "backend": "ollama",
                    "target": preferred.ollama_url,
                    "prompt": prompt,
                    "routing_state": self.routing_state,
                }

        self._restore_cloud_preference()
        return {"backend": "cloud", "target": self.cloud_endpoint, "prompt": prompt, "routing_state": self.routing_state}

    def _discovery_loop(self) -> None:
        while self._running:
            try:
                self.discover_local_nodes()
            except Exception as exc:
                logger.debug(f"Discovery loop error: {exc}")
            time.sleep(self.discovery_interval_seconds)

    def _health_loop(self) -> None:
        while self._running:
            try:
                with self._lock:
                    nodes = list(self.cluster_nodes.values())
                for node in nodes:
                    self.evaluate_node_health(node)
            except Exception as exc:
                logger.debug(f"Health loop error: {exc}")
            time.sleep(self.health_interval_seconds)