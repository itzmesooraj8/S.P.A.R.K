"""
S.P.A.R.K Local Network Topology Mapping
Natively parses ARP cache tables and interface routing data to identify local nodes,
categorizing endpoints (e.g. Nvidia Jetson hardware) without calling cloud services.
"""

import sys
import os
import re
import subprocess
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("SPARK_TOPOLOGY_MAPPER")

class LocalTopologyMapper:
    """Interrogates localized interface telemetry to build a local network node registry."""
    
    # Nvidia OID MAC prefixes (commonly assigned to Jetson developer kits)
    NVIDIA_MAC_PREFIXES = [
        "00:04:4b", "00:41:30", "48:b0:2d", "00:e0:4c", 
        "00-04-4b", "00-41-30", "48-b0-2d", "00-e0-4c"
    ]
    
    def __init__(self):
        self.os_platform = sys.platform

    def run_arp_lookup(self) -> str:
        """Executes system ARP command returning raw table buffer."""
        try:
            if self.os_platform == "win32":
                # Windows ARP cache lookup
                output = subprocess.check_output(
                    ["arp", "-a"], 
                    text=True, 
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
                )
            else:
                # Linux/macOS ARP table lookup
                output = subprocess.check_output(["arp", "-n"], text=True)
            return output
        except Exception as e:
            logger.error(f"Failed executing system ARP lookup command: {e}")
            return ""

    def parse_arp_table(self, raw_arp_data: str) -> List[Dict[str, Any]]:
        """Parses raw shell ARP outputs to extract structured IP/MAC/Type nodes."""
        nodes: List[Dict[str, Any]] = []
        if not raw_arp_data:
            return nodes
            
        # Regex to isolate IP and MAC pairings
        # Matches formats like: 192.168.1.1       00-aa-bb-cc-dd-ee     dynamic
        win_pattern = re.compile(
            r"(?P<ip>\d{1,3}(?:\.\d{1,3}){3})\s+(?P<mac>[0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2}[-:][0-9a-fA-F]{2})\s+(?P<type>\w+)"
        )
        # Matches unix formats like: (192.168.1.1) at 00:aa:bb:cc:dd:ee [ether] on eth0
        unix_pattern = re.compile(
            r"\((?P<ip>\d{1,3}(?:\.\d{1,3}){3})\)\s+at\s+(?P<mac>[0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2}[:-][0-9a-fA-F]{2})"
        )
        
        lines = raw_arp_data.splitlines()
        for line in lines:
            line_clean = line.strip()
            
            # Try Windows pattern
            match = win_pattern.search(line_clean)
            if match:
                ip = match.group("ip")
                mac = match.group("mac")
                node_type = match.group("type")
                nodes.append(self._classify_node(ip, mac, node_type))
                continue
                
            # Try Unix pattern
            match = unix_pattern.search(line_clean)
            if match:
                ip = match.group("ip")
                mac = match.group("mac")
                nodes.append(self._classify_node(ip, mac, "dynamic"))
                
        return nodes

    def _classify_node(self, ip: str, mac: str, link_type: str) -> Dict[str, Any]:
        """Classifies nodes based on known MAC OID vendor mappings."""
        mac_lower = mac.lower()
        is_jetson = False
        
        # Check vendor OIDs
        for prefix in self.NVIDIA_MAC_PREFIXES:
            if mac_lower.startswith(prefix.lower()):
                is_jetson = True
                break
                
        node_role = "auxiliary_jetson_node" if is_jetson else "standard_network_client"
        
        return {
            "ip_address": ip,
            "mac_address": mac,
            "link_type": link_type,
            "role": node_role,
            "hardware_category": "Nvidia Jetson Embedded" if is_jetson else "Generic Endpoint"
        }

    def reconstruct_topology(self) -> Dict[str, Any]:
        """Runs scan pipeline, compiling local topology register maps."""
        raw_data = self.run_arp_lookup()
        parsed_nodes = self.parse_arp_table(raw_data)
        
        jetson_nodes = [n for n in parsed_nodes if n["role"] == "auxiliary_jetson_node"]
        
        return {
            "timestamp": os.getpid(),
            "nodes_discovered": len(parsed_nodes),
            "jetson_nodes_active": len(jetson_nodes),
            "topology_map": parsed_nodes
        }
