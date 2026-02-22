from typing import Dict, Any, List
import time

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
        snapshots = {
            pid: ctx.export_snapshot()
            for pid, ctx in registry.active_projects.items()
        }
        
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
                return rp["lint_errors"] + rp["type_errors"] + (rp["known_vulnerabilities"] * 10) + (rp["unsafe_patterns_detected"] * 5)
                
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
        
        # Guard limits
        system_health_score = max(0.0, min(100.0, system_health_score))
        
        return {
            "analyzed_projects": len(snapshots),
            "timestamp": time.time(),
            "comparative_metrics": comparative_metrics,
            "cross_patterns": cross_patterns[:10],
            "system_health_score": round(system_health_score, 1)
        }

cross_analyzer = CrossProjectAnalyzer()
