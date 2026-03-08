"""SPARK Self-Build — autonomous capability detection and improvement."""
from .capability_manager import get_capability_status, request_install
from .technique_scorer import get_all_techniques, record_technique_result
from .debrief_synthesizer import synthesize_debrief

__all__ = [
    "get_capability_status", "request_install",
    "get_all_techniques", "record_technique_result",
    "synthesize_debrief",
]
