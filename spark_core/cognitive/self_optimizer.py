"""
SPARK Self-Evolution Controller

Bounded self-improvement engine. Analyzes SPARK's own performance metrics
and proposes configuration / strategy adjustments.

Key constraints (safety):
  - NEVER modifies running code automatically
  - ALL proposed changes require human approval (PENDING state)
  - Full audit log of all proposed and applied changes
"""
import json
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

_LOG_PATH = Path(__file__).parent.parent.parent / "spark_memory_db" / "evolution_log.jsonl"


class ChangeStatus(str, Enum):
    PROPOSED  = "PROPOSED"
    APPROVED  = "APPROVED"
    REJECTED  = "REJECTED"
    APPLIED   = "APPLIED"


@dataclass
class EvolutionProposal:
    proposal_id: str
    title: str
    category: str            # "config" | "strategy" | "model_routing" | "threshold"
    description: str
    current_value: Any
    proposed_value: Any
    expected_impact: str
    confidence: float
    status: ChangeStatus = ChangeStatus.PROPOSED
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None
    resolved_by: Optional[str] = None


class SelfEvolutionController:
    """
    SPARK's bounded self-improvement module.
    
    Watches performance signals and proposes targeted configuration adjustments.
    Human approval is MANDATORY before application.
    """

    def __init__(self):
        self._proposals: Dict[str, EvolutionProposal] = {}
        _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        print("🧬 [SelfEvolution] Controller initialized (human-in-the-loop mode).")

    # ── Analysis ─────────────────────────────────────────────────────────────

    def analyze_and_propose(self, metrics: Dict[str, Any]) -> List[EvolutionProposal]:
        """Inspect metrics and generate improvement proposals."""
        new_proposals = []

        # Model routing adjustments
        model_stats = metrics.get("model_stats", {})
        for model_name, stats in model_stats.items():
            if stats.get("avg_latency_ms", 0) > 8000 and stats.get("attempts", 0) > 5:
                p = self._propose(
                    title=f"Deprioritize slow model: {model_name}",
                    category="model_routing",
                    description=f"{model_name} avg latency is {stats['avg_latency_ms']:.0f}ms — above 8s threshold.",
                    current_value={"priority": "default"},
                    proposed_value={"priority": "lower", "max_cost_tier": 1},
                    expected_impact="Reduce first-token latency by routing away from slow models.",
                    confidence=0.70,
                )
                if p:
                    new_proposals.append(p)

        # Memory pressure
        if metrics.get("memory_percent", 0) > 85:
            p = self._propose(
                title="Reduce session memory max_turns",
                category="config",
                description=f"Memory at {metrics['memory_percent']:.0f}% — reduce context window.",
                current_value={"max_turns": 5},
                proposed_value={"max_turns": 3},
                expected_impact="Free ~20% memory by reducing conversation context buffer.",
                confidence=0.80,
            )
            if p:
                new_proposals.append(p)

        # Cognitive loop interval
        cycle_anomalies = metrics.get("consecutive_anomaly_cycles", 0)
        if cycle_anomalies >= 3:
            p = self._propose(
                title="Increase cognitive loop frequency during anomaly streak",
                category="strategy",
                description=f"{cycle_anomalies} consecutive anomaly cycles detected.",
                current_value={"cycle_interval_s": 120},
                proposed_value={"cycle_interval_s": 60},
                expected_impact="Faster anomaly detection and response during elevated threat periods.",
                confidence=0.75,
            )
            if p:
                new_proposals.append(p)

        return new_proposals

    def _propose(
        self, title: str, category: str, description: str,
        current_value: Any, proposed_value: Any,
        expected_impact: str, confidence: float,
    ) -> Optional[EvolutionProposal]:
        # Deduplicate: don't re-propose if same title is already PROPOSED
        for p in self._proposals.values():
            if p.title == title and p.status == ChangeStatus.PROPOSED:
                return None

        proposal = EvolutionProposal(
            proposal_id=str(uuid.uuid4()),
            title=title,
            category=category,
            description=description,
            current_value=current_value,
            proposed_value=proposed_value,
            expected_impact=expected_impact,
            confidence=confidence,
        )
        self._proposals[proposal.proposal_id] = proposal
        self._append_log(proposal)
        print(f"💡 [SelfEvolution] New proposal: {title} (confidence={confidence:.0%})")
        return proposal

    # ── Approval / Rejection ─────────────────────────────────────────────────

    def approve(self, proposal_id: str, approver: str = "human") -> Optional[EvolutionProposal]:
        p = self._proposals.get(proposal_id)
        if not p or p.status != ChangeStatus.PROPOSED:
            return None
        p.status = ChangeStatus.APPROVED
        p.resolved_at = time.time()
        p.resolved_by = approver
        self._append_log(p, event="approved")
        print(f"✅ [SelfEvolution] Proposal approved by {approver}: {p.title}")
        return p

    def reject(self, proposal_id: str, rejector: str = "human") -> Optional[EvolutionProposal]:
        p = self._proposals.get(proposal_id)
        if not p or p.status != ChangeStatus.PROPOSED:
            return None
        p.status = ChangeStatus.REJECTED
        p.resolved_at = time.time()
        p.resolved_by = rejector
        self._append_log(p, event="rejected")
        return p

    def mark_applied(self, proposal_id: str) -> Optional[EvolutionProposal]:
        p = self._proposals.get(proposal_id)
        if not p or p.status != ChangeStatus.APPROVED:
            return None
        p.status = ChangeStatus.APPLIED
        self._append_log(p, event="applied")
        return p

    # ── Query ─────────────────────────────────────────────────────────────────

    def get_proposals(self, status: Optional[ChangeStatus] = None) -> List[Dict[str, Any]]:
        result = []
        for p in sorted(self._proposals.values(), key=lambda x: x.created_at, reverse=True):
            if status is None or p.status == status:
                result.append({
                    "proposal_id": p.proposal_id,
                    "title": p.title,
                    "category": p.category,
                    "description": p.description,
                    "current_value": p.current_value,
                    "proposed_value": p.proposed_value,
                    "expected_impact": p.expected_impact,
                    "confidence": p.confidence,
                    "status": p.status.value,
                    "created_at": p.created_at,
                    "resolved_at": p.resolved_at,
                    "resolved_by": p.resolved_by,
                })
        return result

    # ── Logging ───────────────────────────────────────────────────────────────

    def _append_log(self, proposal: EvolutionProposal, event: str = "proposed"):
        entry = {
            "ts": time.time(),
            "event": event,
            "proposal_id": proposal.proposal_id,
            "title": proposal.title,
            "status": proposal.status.value,
        }
        try:
            with _LOG_PATH.open("a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass


# ── Singleton ─────────────────────────────────────────────────────────────────
self_evolution = SelfEvolutionController()
