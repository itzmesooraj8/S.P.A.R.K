import time
from typing import Dict, Any, List
from intelligence.mutation_log import get_all_mutations
from intelligence.context import context_compiler

HEURISTICS_VERSION = "2.5.1"

class MutationHeuristics:
    @staticmethod
    def analyze_node_history(target_node: str) -> Dict[str, Any]:
        """
        Analyzes past mutations on a specific node to compute a risk profile.
        Returns explicit structured control data to influence future patch generation.
        """
        history = get_all_mutations()
        
        node_records = [r for r in history if r.get("target_node") == target_node]
        
        total_attempts = len(node_records)
        
        if total_attempts == 0:
            return {
                "risk_level": "UNKNOWN",
                "success_rate": 1.0,
                "total_attempts": 0,
                "regression_frequency": 0.0,
                "avg_duration_ms": 0,
                "dominant_errors": [],
                "advice": "No history for this node. Proceed with standard patching."
            }
            
        passed_attempts = sum(1 for r in node_records if r.get("success") is True)
        failed_attempts = total_attempts - passed_attempts
        
        success_rate = passed_attempts / total_attempts if total_attempts > 0 else 0.0
        regression_frequency = failed_attempts / total_attempts if total_attempts > 0 else 0.0
        
        durations = [r.get("duration_ms", 0) for r in node_records if r.get("duration_ms", 0) > 0]
        avg_duration = int(sum(durations) / len(durations)) if durations else 0
        
        # Extract unique errors
        errors = {}
        for r in node_records:
            err = r.get("error_trace")
            if err and err != "Unknown":
                # Take first line of error as signature
                sig = err.split('\n')[0].strip()
                errors[sig] = errors.get(sig, 0) + 1
                
        dominant_errors = sorted([{"error": k, "count": v} for k, v in errors.items()], key=lambda x: x["count"], reverse=True)
        
        # Calculate Risk Index via Stability and Confidence
        stability = success_rate
        confidence = min(total_attempts / 5.0, 1.0)
        
        # Error Pattern Weighting -> If the node throws the identical error repeatedly, it increases risk.
        error_penalty = 0.0
        if dominant_errors:
            max_repeats = dominant_errors[0]["count"]
            if max_repeats > 1:
                # Up to +0.3 risk index penalty for continually hitting the exact same error (shows iteration blindness)
                error_penalty = min((max_repeats - 1) * 0.1, 0.3)
                
        # Volatility Decay -> If the last mutation was a long time ago, confidence decays slightly.
        # Assuming we have timestamp on recent records, let's find the most recent attempt.
        time_decay = 0.0
        latest_attempt_time = max([r.get("timestamp", time.time()) for r in node_records]) if node_records else time.time()
        hours_since_last = (time.time() - latest_attempt_time) / 3600.0
        if hours_since_last > 24.0:
            # Drop confidence slightly if it hasn't been touched in over a day
            confidence = max(0.1, confidence - 0.2)
            
        base_risk = ((1.0 - stability) * confidence) + error_penalty
        
        # Scale risk through Context Compiler downstream architecture entanglement constraints
        context_multiplier = context_compiler.calculate_contextual_risk_modifier(target_node)
        risk_index = base_risk * context_multiplier
        
        # Clamp between 0 and 1
        risk_index = max(0.0, min(risk_index, 1.0))
        
        # Heuristic Risk Assignment
        risk_level = "LOW"
        advice = "Node is stable. Standard patching allowed."
        
        if risk_index > 0.7:
            risk_level = "HIGH"
            advice = "Highly volatile node. Generate smaller diffs. Avoid aggressive structural rewrites. Prefer additive changes."
        elif risk_index >= 0.25:
            risk_level = "MEDIUM"
            advice = "Node has a history of regressions or high uncertainty. Review dominant errors and verify caller trees before mutating."
            
        return {
            "version": HEURISTICS_VERSION,
            "risk_level": risk_level,
            "risk_index": round(risk_index, 2),
            "stability": round(stability, 2),
            "confidence": round(confidence, 2),
            "success_rate": round(success_rate, 2),
            "total_attempts": total_attempts,
            "regression_frequency": round(regression_frequency, 2),
            "avg_duration_ms": avg_duration,
            "dominant_errors": dominant_errors[:5], # Top 5
            "advice": advice
        }

mutation_heuristics = MutationHeuristics()
