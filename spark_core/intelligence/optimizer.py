from typing import Dict, Any, List
from intelligence.trust_layer import trust_store

class OptimizationEngine:
    """
    Phase 3A - Advisory Optimization Engine.
    Reads bounded snapshots and temporal trends to generate deterministic, non-mutating recommendations.
    Strictly isolated from state mutation and execution environments.
    """
    
    @staticmethod
    def generate_recommendations(project_id: str, snapshot: Dict[str, Any], trends: Dict[str, Any]) -> List[Dict[str, Any]]:
        raw_recommendations = []
        
        rp = snapshot.get("risk_profile", {})
        gp = snapshot.get("graph", {})
        
        # 1. Structural Cleanup Suggestions
        if trends.get("structural_drift") == "DECAYING":
            circ_deps = gp.get("circular_dependencies", 0)
            if circ_deps > 0:
                raw_recommendations.append({
                    "id": "opt_structural_drift",
                    "type": "reduce_circular_dependencies",
                    "severity": "high" if circ_deps > 5 else "medium",
                    "base_confidence": 0.85,
                    "message": f"Structural decay detected alongside {circ_deps} circular dependencies. Recommend isolating shared utility layers.",
                    "actionable": True
                })
                
        # 2. Risk Mitigation Suggestions
        if trends.get("risk_trend") == "DEGRADING":
            lint_errs = rp.get("lint_errors", 0)
            if lint_errs > 20:
                raw_recommendations.append({
                    "id": "opt_risk_degrade_lint",
                    "type": "enforce_lint_boundaries",
                    "severity": "medium",
                    "base_confidence": 0.90,
                    "message": f"Risk profile degrading with {lint_errs} lint failures. Recommend implementing strict pre-commit hooks.",
                    "actionable": True
                })
                
        # 3. Mutation Volatility Stabilization Advice
        if trends.get("mutation_volatility") == "HIGH":
            raw_recommendations.append({
                "id": "opt_mutation_volatility",
                "type": "stabilize_churn",
                "severity": "medium",
                "base_confidence": 0.75,
                "message": "High mutation volatility detected. Recommend freezing feature development to focus on architecture stabilization.",
                "actionable": False
            })
            
        # 4. Sandbox Execution Stability
        if not snapshot.get("execution_profile", {}).get("sandbox_active", True):
            raw_recommendations.append({
                "id": "opt_sandbox_offline",
                "type": "restore_execution_boundary",
                "severity": "high",
                "base_confidence": 0.99,
                "message": "Sandbox execution boundary is offline. Mutations cannot be safely verified. Recommend immediate restart.",
                "actionable": True
            })

        trust_metrics = trust_store.compute_trust_metrics(project_id)
        final_recs = []
        
        sev_map = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        for rec in raw_recommendations:
            rec_type = rec["type"]
            base_conf = rec["base_confidence"]
            
            type_trust = trust_metrics["trust_scores"].get(rec_type, {"rts": 0.0, "votes": 0})
            rts = type_trust["rts"]
            votes = type_trust["votes"]
            
            volatility = trends.get("mutation_volatility", "MEDIUM")
            temporal_stability = 0.5 if volatility == "HIGH" else 0.8 if volatility == "MEDIUM" else 1.0
            
            effective_confidence = base_conf * max(0.1, rts) * temporal_stability
            if volatility == "HIGH":
                effective_confidence = min(effective_confidence, 0.5)
                
            sev_num = sev_map.get(rec["severity"], 2)
            
            # Phase 3B Gating Logic
            auto_applicable = False
            # Needs strong RTS (>0.75), high vote count (>=10), safe drift trend, and safe severity.
            if rts >= 0.75 and votes >= 10 and trends.get("risk_trend") != "DEGRADING" and sev_num <= 3:
                auto_applicable = True
                
            final_recs.append({
                "id": rec["id"],
                "type": rec_type,
                "severity": rec["severity"],
                "confidence": round(effective_confidence, 2),
                "base_confidence": base_conf,
                "rts_factor": rts,
                "message": rec["message"],
                "actionable": rec["actionable"],
                "auto_applicable": auto_applicable
            })

        # Cap recommendations to maintain cognitive bounds
        return final_recs[:10]

    def analyze_project(self, project_id: str, snapshot: Dict[str, Any], trends: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesizes the purely advisory optimization plan for a single project context.
        """
        recs = self.generate_recommendations(project_id, snapshot, trends)
        
        return {
            "project_id": project_id,
            "status": "ADVISORY_ONLY",
            "recommendation_count": len(recs),
            "recommendations": recs
        }

optimizer = OptimizationEngine()
