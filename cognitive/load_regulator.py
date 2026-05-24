from __future__ import annotations

class CognitiveLoadRegulator:
    """Limits conversational verbosity under critical processor stress or tool latencies."""
    def __init__(self, latency_threshold_ms: float = 800.0):
        self.latency_threshold = latency_threshold_ms

    def regulate_response(self, verbal_reply: str, current_latency_ms: float, system_cpu_percent: float) -> str:
        if current_latency_ms > self.latency_threshold or system_cpu_percent > 85.0:
            sentences = verbal_reply.split('.')
            if len(sentences) > 0:
                # Truncate and prep alert indicator
                return f"[CHOKED ALERT] Status: OK. {sentences[0].strip()}."
        return verbal_reply
