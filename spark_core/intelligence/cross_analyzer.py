from typing import Dict, Any, List
import time
from intelligence.pattern_memory import pattern_store
from intelligence.trust_layer import trust_store

class CrossProjectAnalyzer:
    """
    Read-only meta-cognition layer.
    Observes and synthesizes patterns across completely isolated ProjectContexts.
    Zero write access to ensure strict process boundary preservation.
    """
    
    @staticmethod
    def analyze_all(registry) -> Dict[str, Any]:
        """
        Pulls synchronized, sanitized snapshots from all active project boundaries,
        and evaluates them for architectural, security, and mutational similarities.
        """
        snapshots = {}
        for pid, ctx in registry.active_projects.items():
            snap = ctx.export_snapshot()
            if "error" not in snap:
                snapshots[pid] = snap
        
        comparative_metrics = {
            "largest_project": "None",
            "most_complex_project": "None",
            "highest_risk_project": "None",
            "most_active_project": "None",
        }
        
        cross_patterns: List[Dict[str, Any]] = []
        system_health_score = 100.0
        
        if snapshots:
            def risk_score(s):
                rp = s["risk_profile"]
                gp = s["graph"]
                mp = s["mutation_profile"]
                loc = max(1, s["resource_profile"].get("estimated_loc", 1))
                mutation_density = float(mp.get("total_mutations", 0)) / loc
                return (rp.get("lint_errors", 0) * 0.5 + 
                        rp.get("type_errors", 0) * 0.8 + 
                        (rp.get("known_vulnerabilities", 0) * 2.0) + 
                        (gp.get("circular_dependencies", 0) * 1.2) + 
                        (mutation_density * 0.5))
                
            # Compute extremes
            comparative_metrics["largest_project"] = max(
                snapshots.keys(), 
                key=lambda k: snapshots[k]["resource_profile"]["estimated_loc"]
            )
            comparative_metrics["most_complex_project"] = max(
                snapshots.keys(), 
                key=lambda k: snapshots[k]["graph"]["dependency_edges"] + snapshots[k]["graph"]["circular_dependencies"] * 5
            )
            comparative_metrics["highest_risk_project"] = max(
                snapshots.keys(), 
                key=lambda k: risk_score(snapshots[k])
            )
            comparative_metrics["most_active_project"] = max(
                snapshots.keys(), 
                key=lambda k: snapshots[k]["mutation_profile"]["recent_mutations_24h"]
            )
            
            # Detect behavioral and structural metadata across boundaries
            
            # 1. Repeated Lint Failures / Risk Profile Elements
            high_risk_projects = [k for k, v in snapshots.items() if risk_score(v) > 20]
            if high_risk_projects:
                cross_patterns.append({
                    "pattern_type": "elevated_risk_profile",
                    "projects": high_risk_projects[:5],
                    "severity": "high"
                })
                system_health_score -= 15 * len(high_risk_projects)
            
            # 2. High Circular Dependency Cluster
            high_circ_projects = [k for k, v in snapshots.items() if v["graph"]["circular_dependencies"] > 5]
            if high_circ_projects:
                cross_patterns.append({
                    "pattern_type": "high_circular_dependency_cluster",
                    "projects": high_circ_projects[:5],
                    "severity": "medium"
                })
                system_health_score -= 5 * len(high_circ_projects)

            # 3. High Mutation Churn (Behavioral Marker)
            high_churn_projects = [k for k, v in snapshots.items() if v["mutation_profile"]["recent_mutations_24h"] > 50]
            if high_churn_projects:
                cross_patterns.append({
                    "pattern_type": "high_mutation_churn",
                    "projects": high_churn_projects[:5],
                    "severity": "low"
                })
                
            # 4. Sandbox Execution Stability
            offline_sandboxes = [k for k, v in snapshots.items() if not v["execution_profile"]["sandbox_active"]]
            if offline_sandboxes:
                cross_patterns.append({
                    "pattern_type": "execution_boundary_offline",
                    "projects": offline_sandboxes[:5],
                    "severity": "low"
                })
                system_health_score -= 2 * len(offline_sandboxes)
        
        # Inject snapshots into Temporal Database
        pattern_store.ingest(snapshots, snapshots)
        
        # Pull trends per project to modify base health
        project_trends = {}
        feedback_metrics = {}
        interpretations = {}
        for pid in snapshots.keys():
            trend = pattern_store.compute_trends(pid)
            project_trends[pid] = trend
            feedback_metrics[pid] = trust_store.compute_trust_metrics(pid)
            
            interp = []
            snap = snapshots[pid]
            rp = snap.get("risk_profile", {})
            gp = snap.get("graph", {})
            mp = snap.get("mutation_profile", {})
            
            if rp.get("lint_errors", 0) > 0 and trend.get("risk_trend") == "DEGRADING":
                interp.append("Code quality is deteriorating. New changes are introducing style or structural violations.")
            if gp.get("circular_dependencies", 0) > 0 and trend.get("structural_drift") == "DECAYING":
                interp.append("Architectural boundary erosion detected. Modules are becoming cyclically coupled.")
            if mp.get("recent_mutations_24h", 0) > 10 and trend.get("risk_trend") == "STABLE":
                interp.append("High development velocity detected without quality regression.")
                
            interpretations[pid] = " ".join(interp) if interp else "System is performing nominally."
            
            # Predictively penalize health score based on degrading trajectories
            if trend.get("structural_drift") == "DECAYING":
                system_health_score -= 5
            if trend.get("risk_trend") == "DEGRADING":
                system_health_score -= 10
        
        # Guard limits
        system_health_score = max(0.0, min(100.0, system_health_score))
        
        # Scrub raw snapshots out of the return dict since memory footprint must stay O(1)
        # We only emit bounded data to the caller/HUD
        return {
            "analyzed_projects": len(snapshots),
            "timestamp": time.time(),
            "comparative_metrics": comparative_metrics,
            "cross_patterns": cross_patterns[:10],
            "project_trends": project_trends,
            "interpretations": interpretations,
            "feedback_metrics": feedback_metrics,
            "system_health_score": round(system_health_score, 1)
        }

cross_analyzer = CrossProjectAnalyzer()
