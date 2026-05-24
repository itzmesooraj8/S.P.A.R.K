from __future__ import annotations

import os

class SystemContextMapper:
    def __init__(self, db_path: str = "knowledge_base/chroma_db"):
        self.db_path = db_path

    def get_attention_context(self, user_query: str) -> str:
        """Retrieves relevant environmental, system, and hardware variables for query injection."""
        normalized = user_query.lower()
        if "cpu" in normalized or "performance" in normalized or "telemetry" in normalized:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            return f"[SYSTEM CONTEXT] Telemetry coordinates: CPU at {cpu}%, RAM at {ram}%."
        
        # Fallback empty string
        return ""
