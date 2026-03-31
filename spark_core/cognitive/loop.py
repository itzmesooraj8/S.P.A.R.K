"""
SPARK Cognitive Loop — Autonomous Reasoning Engine

Implements the core cognitive cycle:
    Observe → Analyze → Hypothesize → Plan → Execute → Reflect → Update Memory

Runs as a background asyncio task. Interval is configurable.
Each phase emits events to the EventBus for observability.
"""
import asyncio
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from system.event_bus import event_bus


class CognitivePhase(str, Enum):
    IDLE        = "IDLE"
    OBSERVING   = "OBSERVING"
    ANALYZING   = "ANALYZING"
    PLANNING    = "PLANNING"
    EXECUTING   = "EXECUTING"
    REFLECTING  = "REFLECTING"
    UPDATING    = "UPDATING"


@dataclass
class CognitiveCycle:
    cycle_id: str
    started_at: float
    observations: List[Dict[str, Any]] = field(default_factory=list)
    analysis: Optional[str] = None
    hypothesis: Optional[str] = None
    plan: List[str] = field(default_factory=list)
    execution_results: List[Dict[str, Any]] = field(default_factory=list)
    reflection: Optional[str] = None
    completed_at: Optional[float] = None
    anomalies_detected: int = 0
    confidence: float = 0.5


class AutonomousCognitiveLoop:
    """
    SPARK's self-reasoning background process.
    
    Every `cycle_interval_s` seconds, SPARK:
    1. OBSERVE   — collect system state, globe events, agent results, memory
    2. ANALYZE   — identify patterns, anomalies, emerging situations
    3. PLAN      — determine if autonomous action is needed
    4. EXECUTE   — dispatch sub-tasks to agents (bounded, non-destructive)
    5. REFLECT   — evaluate cycle outcomes
    6. UPDATE    — persist insights to knowledge graph
    """

    def __init__(self, cycle_interval_s: int = 120):
        self.cycle_interval_s = cycle_interval_s
        self.phase = CognitivePhase.IDLE
        self.cycle_count = 0
        self.last_cycle: Optional[CognitiveCycle] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._introspection_data: Dict[str, Any] = {}
        print(f"🔮 [CognitiveLoop] Initialized. Cycle interval: {cycle_interval_s}s")

    def start(self):
        print("🔮 [CognitiveLoop] Autonomous reasoning DISABLED by Jarvis config (waiting for explicit user command).")
        # if not self._running:
        #     self._running = True
        #     self._task = asyncio.create_task(self._loop())
        #     print("🔮 [CognitiveLoop] Autonomous reasoning started.")

    def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()

    def inject_observation(self, data: Dict[str, Any]):
        """External systems can push observations into the loop."""
        self._introspection_data.update(data)

    async def _loop(self):
        """Main loop — waits for interval then runs one full cycle."""
        # Initial delay — let the system fully boot first
        await asyncio.sleep(30)
        while self._running:
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                print(f"❌ [CognitiveLoop] Cycle error: {exc}")
                event_bus.publish("cognitive_error", {"error": str(exc), "phase": self.phase.value})
            await asyncio.sleep(self.cycle_interval_s)

    async def _run_cycle(self):
        cycle = CognitiveCycle(
            cycle_id=str(uuid.uuid4()),
            started_at=time.time(),
        )
        self.cycle_count += 1
        print(f"🔮 [CognitiveLoop] ── Cycle #{self.cycle_count} starting ──")

        # ── Phase 1: OBSERVE ─────────────────────────────────────────────────
        self.phase = CognitivePhase.OBSERVING
        event_bus.publish("cognitive_phase", {"phase": "OBSERVING", "cycle": self.cycle_count})
        cycle.observations = await self._observe()

        # ── Phase 2: ANALYZE ─────────────────────────────────────────────────
        self.phase = CognitivePhase.ANALYZING
        event_bus.publish("cognitive_phase", {"phase": "ANALYZING", "cycle": self.cycle_count})
        analysis, anomalies = await self._analyze(cycle.observations)
        cycle.analysis = analysis
        cycle.anomalies_detected = anomalies

        # ── Phase 3: PLAN ────────────────────────────────────────────────────
        self.phase = CognitivePhase.PLANNING
        event_bus.publish("cognitive_phase", {"phase": "PLANNING", "cycle": self.cycle_count})
        plan = await self._plan(cycle.analysis, cycle.observations)
        cycle.plan = plan

        # ── Phase 4: EXECUTE ─────────────────────────────────────────────────
        if plan:
            self.phase = CognitivePhase.EXECUTING
            event_bus.publish("cognitive_phase", {"phase": "EXECUTING", "cycle": self.cycle_count, "actions": plan})
            results = await self._execute(plan)
            cycle.execution_results = results

        # ── Phase 5: REFLECT ─────────────────────────────────────────────────
        self.phase = CognitivePhase.REFLECTING
        event_bus.publish("cognitive_phase", {"phase": "REFLECTING", "cycle": self.cycle_count})
        reflection = await self._reflect(cycle)
        cycle.reflection = reflection

        # ── Phase 6: UPDATE MEMORY ───────────────────────────────────────────
        self.phase = CognitivePhase.UPDATING
        await self._update_memory(cycle)

        cycle.completed_at = time.time()
        cycle.confidence = self._compute_confidence(cycle)
        self.last_cycle = cycle
        self.phase = CognitivePhase.IDLE

        elapsed = round(cycle.completed_at - cycle.started_at, 2)
        print(f"🔮 [CognitiveLoop] ── Cycle #{self.cycle_count} done in {elapsed}s | "
              f"anomalies={cycle.anomalies_detected} | confidence={cycle.confidence:.2f} ──")

        event_bus.publish("cognitive_cycle_done", {
            "cycle_id": cycle.cycle_id,
            "cycle_number": self.cycle_count,
            "elapsed_s": elapsed,
            "anomalies": cycle.anomalies_detected,
            "plan_actions": len(cycle.plan),
            "confidence": cycle.confidence,
            "reflection": cycle.reflection,
        })

    # ── Phase implementations ─────────────────────────────────────────────────

    async def _observe(self) -> List[Dict[str, Any]]:
        """Gather observations from all available data sources."""
        observations = []
        now = time.time()

        # System state
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=0.5)
            mem = psutil.virtual_memory()
            observations.append({
                "source": "system", "type": "metrics",
                "data": {"cpu_pct": cpu, "mem_pct": mem.percent, "timestamp": now}
            })
            if cpu > 85:
                observations.append({
                    "source": "system", "type": "anomaly",
                    "severity": "HIGH", "message": f"CPU usage critical: {cpu}%"
                })
            if mem.percent > 90:
                observations.append({
                    "source": "system", "type": "anomaly",
                    "severity": "HIGH", "message": f"Memory usage critical: {mem.percent}%"
                })
        except Exception:
            pass

        # Injected external observations (e.g. from globe broadcaster)
        for key, val in self._introspection_data.items():
            observations.append({"source": "external", "type": key, "data": val, "ts": now})
        self._introspection_data.clear()

        # Recent memory observations
        try:
            from memory.graph_memory import knowledge_graph
            recent = await knowledge_graph.get_recent_observations(limit=10, min_importance=0.7)
            if recent:
                observations.append({
                    "source": "memory", "type": "recent_observations",
                    "data": recent, "ts": now
                })
        except Exception:
            pass

        return observations

    async def _analyze(self, observations: List[Dict[str, Any]]) -> tuple[str, int]:
        """Pattern-match observations and count anomalies."""
        anomalies = sum(1 for o in observations if o.get("type") == "anomaly")
        summary_parts = []
        for obs in observations:
            src = obs.get("source", "?")
            typ = obs.get("type", "?")
            if typ == "anomaly":
                summary_parts.append(f"⚠️ ANOMALY [{obs.get('severity','?')}]: {obs.get('message', '')}")
            elif typ == "metrics":
                d = obs.get("data", {})
                summary_parts.append(f"📊 System: CPU={d.get('cpu_pct',0):.0f}% MEM={d.get('mem_pct',0):.0f}%")
        analysis = "\n".join(summary_parts) if summary_parts else "No significant observations."
        return analysis, anomalies

    async def _plan(self, analysis: str, observations: List[Dict[str, Any]]) -> List[str]:
        """Determine autonomous actions. Conservative — only diagnostic/monitoring tasks."""
        plan = []
        # Only act if anomalies are present
        anomaly_obs = [o for o in observations if o.get("type") == "anomaly"]
        for obs in anomaly_obs:
            sev = obs.get("severity", "LOW")
            msg = obs.get("message", "")
            if sev in ("HIGH", "CRITICAL"):
                plan.append(f"ALERT: {msg}")
            elif sev == "MEDIUM":
                plan.append(f"MONITOR: {msg}")
        return plan

    async def _execute(self, plan: List[str]) -> List[Dict[str, Any]]:
        """Execute planned actions (currently: emit alerts only — bounded automation)."""
        results = []
        for action in plan:
            if action.startswith("ALERT:"):
                event_bus.publish("spark_alert", {
                    "level": "HIGH",
                    "message": action[7:].strip(),
                    "source": "cognitive_loop",
                })
                results.append({"action": action, "status": "emitted"})
            else:
                results.append({"action": action, "status": "logged"})
        return results

    async def _reflect(self, cycle: CognitiveCycle) -> str:
        """Summarize what happened this cycle."""
        parts = [
            f"Cycle #{self.cycle_count}: {len(cycle.observations)} observations",
            f"Anomalies detected: {cycle.anomalies_detected}",
            f"Actions planned: {len(cycle.plan)}",
            f"Actions executed: {len(cycle.execution_results)}",
        ]
        if cycle.analysis:
            parts.append(f"Analysis: {cycle.analysis[:200]}")
        return " | ".join(parts)

    async def _update_memory(self, cycle: CognitiveCycle):
        """Persist high-importance insights to knowledge graph."""
        if cycle.anomalies_detected > 0 or cycle.reflection:
            try:
                from memory.graph_memory import knowledge_graph
                await knowledge_graph.add_observation(
                    content=cycle.reflection or "Cognitive cycle completed",
                    importance=min(0.5 + cycle.anomalies_detected * 0.2, 1.0),
                    tags=["cognitive_cycle", f"cycle_{self.cycle_count}"],
                )
            except Exception as exc:
                print(f"⚠️ [CognitiveLoop] Memory update failed: {exc}")

    def _compute_confidence(self, cycle: CognitiveCycle) -> float:
        """Estimate cycle confidence based on data richness."""
        base = 0.5
        if len(cycle.observations) > 3:
            base += 0.1
        if cycle.analysis and len(cycle.analysis) > 50:
            base += 0.1
        if cycle.anomalies_detected == 0:
            base += 0.1
        if len(cycle.execution_results) > 0:
            base += 0.1
        return min(base, 1.0)

    def get_status(self) -> Dict[str, Any]:
        last = None
        if self.last_cycle:
            last = {
                "cycle_id": self.last_cycle.cycle_id,
                "completed_at": self.last_cycle.completed_at,
                "anomalies": self.last_cycle.anomalies_detected,
                "confidence": self.last_cycle.confidence,
                "reflection": self.last_cycle.reflection,
                "plan_count": len(self.last_cycle.plan),
            }
        return {
            "running": self._running,
            "phase": self.phase.value,
            "cycle_count": self.cycle_count,
            "cycle_interval_s": self.cycle_interval_s,
            "last_cycle": last,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
cognitive_loop = AutonomousCognitiveLoop(cycle_interval_s=120)
