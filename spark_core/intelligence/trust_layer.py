from typing import Dict, List, Any
import time

class TrustQuantificationLayer:
    """
    Phase 3B - Quantified Human Feedback Loop (Pre-Execution Layer)
    Stores bounded structured telemetry and computes Recommendation Trust Score (RTS).
    Prevents silent drift by requiring mathematically bounded reinforcement.
    """
    
    def __init__(self, max_frames: int = 200):
        self.max_frames = max_frames
        # Dictionary mapping project_id -> List of FeedbackFrame
        self.feedback_history: Dict[str, List[Dict[str, Any]]] = {}
        
    def ingest_feedback(self, project_id: str, rec_type: str, severity: int, confidence: float, user_action: int, user_weight: float = 1.0):
        if project_id not in self.feedback_history:
            self.feedback_history[project_id] = []
            
        frame = {
            "timestamp": time.time(),
            "recommendation_type": rec_type,
            "severity": severity,
            "confidence": confidence,
            "user_action": user_action, # +1 for approve, -1 for reject
            "user_weight": user_weight
        }
        
        self.feedback_history[project_id].append(frame)
        
        # Enforce max bounds via slice
        if len(self.feedback_history[project_id]) > self.max_frames:
            self.feedback_history[project_id] = self.feedback_history[project_id][-self.max_frames:]
            
    def compute_trust_metrics(self, project_id: str) -> Dict[str, Any]:
        """
        Computes RTS (Recommendation Trust Score) per recommendation type and overall automation readiness.
        """
        frames = self.feedback_history.get(project_id, [])
        metrics = {
            "vote_count": len(frames),
            "trust_scores": {},
            "automation_candidates": [],
            "overall_trust": 0.0
        }
        
        if not frames:
            return metrics
            
        type_frames = {}
        for f in frames:
            t = f["recommendation_type"]
            if t not in type_frames:
                type_frames[t] = []
            type_frames[t].append(f)
            
        overall_score_num = 0.0
        overall_score_den = 0.0
        
        for t, tf in type_frames.items():
            total_weight = sum(f["user_weight"] for f in tf)
            if total_weight == 0:
                continue
                
            approved_weight = sum(f["user_weight"] for f in tf if f["user_action"] > 0)
            rejected_weight = sum(f["user_weight"] for f in tf if f["user_action"] < 0)
            
            # RTS = (Approved - Rejected) / Total, bounds restricted
            rts = (approved_weight - rejected_weight) / total_weight
            rts_normalized = max(0.0, min(1.0, rts))
            
            metrics["trust_scores"][t] = {
                "rts": round(rts_normalized, 2),
                "votes": len(tf)
            }
            
            # Automation Candidate Gate Validation
            if rts_normalized >= 0.75 and len(tf) >= 10:
                metrics["automation_candidates"].append(t)
                
            overall_score_num += rts_normalized * total_weight
            overall_score_den += total_weight
            
        if overall_score_den > 0:
            metrics["overall_trust"] = round(overall_score_num / overall_score_den, 2)
            
        return metrics

trust_store = TrustQuantificationLayer()
