from typing import Dict, List, Any
import time

class PatternMemoryStore:
    """
    Longitudinal intelligence layer.
    Observes CrossProjectAnalyzer snapshots and distills them into persistent scalar trends.
    Strictly bounded, stateless beyond defined window sizes.
    """
    
    def __init__(self, max_frames: int = 100):
        self.max_frames = max_frames
        self.history: Dict[str, List[Dict[str, float]]] = {}
        
    def ingest(self, analysis_result: Dict[str, Any], raw_snapshots: Dict[str, Any]):
        """
        Receives the output of CrossProjectAnalyzer alongside the pure snapshots.
        Strips away all AST, topological mapping, and structural layout data.
        Retains only scalar risk, complexity, and behavioral mutations.
        """
        current_time = time.time()
        
        for pid, snap in raw_snapshots.items():
            if pid not in self.history:
                self.history[pid] = []
                
            rp = snap.get("risk_profile", {})
            gp = snap.get("graph", {})
            mp = snap.get("mutation_profile", {})
            
            # Derived scalars
            circular_deps = gp.get("circular_dependencies", 0)
            lint_errors = rp.get("lint_errors", 0)
            vulns = rp.get("known_vulnerabilities", 0)
            
            loc = snap.get("resource_profile", {}).get("estimated_loc", 1)
            mutation_density = float(mp.get("total_mutations", 0)) / max(1, loc)
            
            risk_score = float(
                lint_errors * 0.5 + 
                rp.get("type_errors", 0) * 0.8 + 
                (vulns * 2.0) + 
                (circular_deps * 1.2) + 
                (mutation_density * 0.5)
            )
            
            frame = {
                "timestamp": current_time,
                "circular_dependencies": float(circular_deps),
                "lint_errors": float(lint_errors),
                "mutation_density": mutation_density,
                "risk_score": risk_score
            }
            
            self.history[pid].append(frame)
            
            # Hard Bound Enforcement
            if len(self.history[pid]) > self.max_frames:
                # O(1) slice instead of pop(0) scaling cost
                self.history[pid] = self.history[pid][-self.max_frames:]
                
    def compute_trends(self, project_id: str) -> Dict[str, Any]:
        """
        Calculates deterministically bounded trend slopes over the active window.
        Provides indicators for structural decay or mutation churn without raw state storage.
        """
        frames = self.history.get(project_id, [])
        if len(frames) < 2:
            return {
                "risk_trend": "STABLE",
                "mutation_volatility": "LOW",
                "structural_drift": "STABLE",
                "risk_slope": 0.0,
                "projected_risk_7d": 0.0,
                "projected_trend": "Stable System",
                "data_points": len(frames)
            }
            
        # Linear slope computation: (y_last - y_first) / points
        # For a true time-series regression we'd project slope over timestamp deltas.
        # But Phase 2.5 mandates simplicity: moving average boundaries.
        
        first = frames[0]
        last = frames[-1]
        n = len(frames)
        
        risk_slope = (last["risk_score"] - first["risk_score"]) / n
        mutation_variance = max(f["mutation_density"] for f in frames) - min(f["mutation_density"] for f in frames)
        circ_slope = (last["circular_dependencies"] - first["circular_dependencies"]) / n
        
        # 7-day projection modeling (assuming 'n' represents ~daily or per-run frames over an active window)
        # We will normalize risk_slope to approximate per-day if we assume ticks are per hour, 
        # but realistically we just multiply slope by an arbitrary forward window (e.g., 7 ticks).
        projected_risk_7d = max(0.0, last["risk_score"] + (risk_slope * 7 * 24))
        
        projected_trend = "Stable System"
        if risk_slope > 0.5:
            projected_trend = "Escalating Risk"
        elif risk_slope < -0.5:
            projected_trend = "Improving Stability"
        
        return {
            "risk_trend": "DEGRADING" if risk_slope > 0.5 else "IMPROVING" if risk_slope < -0.5 else "STABLE",
            "mutation_volatility": "HIGH" if mutation_variance > 0.5 else "MEDIUM" if mutation_variance > 0.1 else "LOW",
            "structural_drift": "DECAYING" if circ_slope > 0 else "STABLE",
            "risk_slope": round(risk_slope, 4),
            "projected_risk_7d": round(projected_risk_7d, 2),
            "projected_trend": projected_trend,
            "data_points": n
        }

pattern_store = PatternMemoryStore()
