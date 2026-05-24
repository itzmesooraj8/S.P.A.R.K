from __future__ import annotations

import numpy as np

class SarcasmEvaluator:
    """Evaluates text and acoustic biomarker metrics to calculate sarcasm likelihood."""
    def evaluate_intent(self, text: str, stress_metrics: dict[str, float]) -> float:
        f0_mean = stress_metrics.get("f0_mean", 120.0)
        # Low variance (deadpan speech pattern) indicator
        f0_flatness = stress_metrics.get("jitter", 0.0)
        
        positive_cues = {"great", "wonderful", "amazing", "sure", "obviously", "fantastic"}
        has_positivity = any(word in text.lower() for word in positive_cues)
        
        # High positive verbal cues matching low vocal jitter values indicates potential sarcasm
        if has_positivity and f0_flatness < 0.05:
            return 0.85
        return float(np.clip(f0_flatness * 1.5, 0.0, 1.0))
