"""
S.P.A.R.K Automated Log Synthesis & De-Noising
Applies regex tokenization and sliding frequency filters to compress raw multi-agent logs,
yielding highly summarized JSON streams mapping back to root actions.
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("SPARK_LOG_SYNTHESIS")

class LogSynthesizer:
    """Filters log streams, compressing repetitive boilerplate messages to structured JSON summaries."""
    
    def __init__(self, frequency_window: int = 10):
        self.frequency_window = frequency_window
        # Regex tokens mapping raw logs to normalized semantic buckets
        self.rules: Dict[str, re.Pattern] = {
            "heartbeat": re.compile(r"(heartbeat|ping|pulse|tick|alive)", re.IGNORECASE),
            "db_query": re.compile(r"(select|insert|update|delete|chromadb|collection|query|sqlite)", re.IGNORECASE),
            "network_poll": re.compile(r"(connection|socket|ip|port|host|arp|dns|http|request)", re.IGNORECASE),
            "gui_action": re.compile(r"(click|mouse|hover|pyautogui|coordinate|screen|grab)", re.IGNORECASE),
            "llm_inference": re.compile(r"(ollama|groq|token|inference|llm|chat|completion|reply)", re.IGNORECASE)
        }
        self.history: List[Dict[str, Any]] = []

    def synthesize_stream(self, raw_lines: List[str]) -> str:
        """Parses a block of log lines and outputs a compressed JSON summary array."""
        synthesized: List[Dict[str, Any]] = []
        
        # Accumulators to collapse consecutive duplicate categories
        current_category: Optional[str] = None
        current_count = 0
        current_sample = ""
        
        for line in raw_lines:
            line = line.strip()
            if not line:
                continue
                
            matched_category = "general_runtime"
            for category, pattern in self.rules.items():
                if pattern.search(line):
                    matched_category = category
                    break
            
            if matched_category == current_category:
                current_count += 1
            else:
                # Flush previous group
                if current_category:
                    synthesized.append({
                        "category": current_category,
                        "raw_occurrences": current_count,
                        "sample_log": current_sample,
                        "summary": f"Collapsed {current_count} lines of raw {current_category} telemetry logs."
                    })
                # Reset to new group
                current_category = matched_category
                current_count = 1
                current_sample = line[:150]
                
        # Final flush
        if current_category:
            synthesized.append({
                "category": current_category,
                "raw_occurrences": current_count,
                "sample_log": current_sample,
                "summary": f"Collapsed {current_count} lines of raw {current_category} telemetry logs."
            })
            
        # Write to local state history
        self.history.extend(synthesized)
        return json.dumps(synthesized, indent=2)

    def get_high_density_summary(self) -> Dict[str, Any]:
        """Provides an aggregated count of all logs processed by category."""
        counts = {}
        for entry in self.history:
            cat = entry["category"]
            counts[cat] = counts.get(cat, 0) + entry["raw_occurrences"]
            
        return {
            "total_raw_processed": sum(counts.values()),
            "category_aggregations": counts,
            "status": "de-noised nominal log state"
        }
