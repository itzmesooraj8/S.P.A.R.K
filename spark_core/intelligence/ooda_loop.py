"""
SPARK OODA loop (Observe -> Orient -> Decide -> Act).

Runs as an autonomous background task and publishes live status updates for HUD.
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from globe.predictor import threat_predictor
from memory.graph_memory import knowledge_graph
from system.event_bus import event_bus


@dataclass
class OODACycle:
    cycle_id: str
    started_at: float
    observed: Dict[str, Any]
    oriented: Dict[str, Any]
    decision: Dict[str, Any]
    action: Dict[str, Any]
    completed_at: float


class OODALoop:
    def __init__(self, cycle_interval_s: int = 60):
        self.cycle_interval_s = max(15, int(cycle_interval_s))
        self.phase = "IDLE"
        self.cycle_count = 0
        self.running = False
        self.last_cycle: Optional[OODACycle] = None

        self._task: Optional[asyncio.Task] = None
        self._alert_cooldown_s = max(30, int(os.getenv("SPARK_OODA_ALERT_COOLDOWN_SECONDS", "180")))
        self._risk_threshold = float(os.getenv("SPARK_OODA_ALERT_RISK", "65"))
        self._last_alert_at = 0.0

    def get_status(self) -> Dict[str, Any]:
        last_cycle = None
        if self.last_cycle:
            elapsed = max(0.0, self.last_cycle.completed_at - self.last_cycle.started_at)
            last_cycle = {
                "cycle_id": self.last_cycle.cycle_id,
                "started_at": self.last_cycle.started_at,
                "completed_at": self.last_cycle.completed_at,
                "elapsed_s": round(elapsed, 2),
                "observed": self.last_cycle.observed,
                "oriented": self.last_cycle.oriented,
                "decision": self.last_cycle.decision,
                "action": self.last_cycle.action,
            }

        return {
            "running": self.running,
            "phase": self.phase,
            "cycle_count": self.cycle_count,
            "cycle_interval_s": self.cycle_interval_s,
            "alert_risk_threshold": self._risk_threshold,
            "alert_cooldown_s": self._alert_cooldown_s,
            "last_cycle": last_cycle,
        }

    async def _publish_status(self):
        event_bus.publish("ooda_status_update", self.get_status())

    def start(self):
        if self._task and not self._task.done():
            return
        self.running = True
        self.phase = "IDLE"
        self._task = asyncio.create_task(self._loop(), name="spark_ooda_loop")
        print(f"[OODA] Started (interval={self.cycle_interval_s}s)")

    def stop(self):
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
        self._task = None
        self.phase = "IDLE"
        print("[OODA] Stopped")

    async def _loop(self):
        # Give the rest of SPARK a short warm-up window.
        await asyncio.sleep(20)
        await self._publish_status()

        while self.running:
            try:
                await self._run_cycle()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                print(f"[OODA] Cycle error: {exc}")
            await asyncio.sleep(self.cycle_interval_s)

    async def _run_cycle(self):
        cycle_id = str(uuid.uuid4())
        started_at = time.time()
        self.cycle_count += 1

        self.phase = "OBSERVE"
        observed = await self._observe()
        await self._publish_status()

        self.phase = "ORIENT"
        oriented = await self._orient(observed)
        await self._publish_status()

        self.phase = "DECIDE"
        decision = await self._decide(oriented)
        await self._publish_status()

        self.phase = "ACT"
        action = await self._act(oriented, decision)

        completed_at = time.time()
        self.last_cycle = OODACycle(
            cycle_id=cycle_id,
            started_at=started_at,
            observed=observed,
            oriented=oriented,
            decision=decision,
            action=action,
            completed_at=completed_at,
        )

        self.phase = "IDLE"
        await self._publish_status()

    async def _observe(self) -> Dict[str, Any]:
        summary = threat_predictor.get_global_threat_summary()
        recent = await knowledge_graph.get_recent_observations(limit=12, min_importance=0.6)

        return {
            "global_risk_score": float(summary.get("global_risk_score", 0.0)),
            "global_risk_level": str(summary.get("global_risk_level", "LOW")),
            "hotspots": int(summary.get("hotspots", 0)),
            "top_regions": summary.get("top_regions", [])[:5],
            "recent_observations": len(recent),
        }

    async def _orient(self, observed: Dict[str, Any]) -> Dict[str, Any]:
        risk_score = float(observed.get("global_risk_score", 0.0))
        hotspots = int(observed.get("hotspots", 0))

        urgency = "low"
        if risk_score >= 80 or hotspots >= 5:
            urgency = "critical"
        elif risk_score >= self._risk_threshold or hotspots >= 3:
            urgency = "high"
        elif risk_score >= 40 or hotspots >= 1:
            urgency = "medium"

        return {
            "urgency": urgency,
            "risk_score": round(risk_score, 2),
            "hotspots": hotspots,
            "risk_level": observed.get("global_risk_level", "LOW"),
            "context": (
                f"Global risk {round(risk_score, 1)} with {hotspots} hotspots"
            ),
        }

    async def _decide(self, oriented: Dict[str, Any]) -> Dict[str, Any]:
        urgency = str(oriented.get("urgency", "low"))
        risk_score = float(oriented.get("risk_score", 0.0))

        now = time.monotonic()
        cooldown_elapsed = (now - self._last_alert_at) >= self._alert_cooldown_s

        if urgency in {"high", "critical"} and risk_score >= self._risk_threshold and cooldown_elapsed:
            return {
                "should_alert": True,
                "action": "emit_alert",
                "reason": "risk threshold crossed",
                "confidence": 0.85 if urgency == "high" else 0.95,
            }

        return {
            "should_alert": False,
            "action": "monitor",
            "reason": "no threshold breach or cooldown active",
            "confidence": 0.7,
        }

    async def _act(self, oriented: Dict[str, Any], decision: Dict[str, Any]) -> Dict[str, Any]:
        if not decision.get("should_alert"):
            return {
                "status": "idle",
                "message": "Monitoring only",
            }

        self._last_alert_at = time.monotonic()

        body = (
            f"OODA alert: {oriented.get('context')} | urgency={oriented.get('urgency')}"
        )
        event_bus.publish(
            "spark_alert",
            {
                "severity": "warning" if oriented.get("urgency") == "high" else "critical",
                "title": "OODA Proactive Alert",
                "body": body,
                "source": "ooda_loop",
            },
        )

        return {
            "status": "alert_emitted",
            "message": body,
        }


ooda_loop = OODALoop(cycle_interval_s=int(os.getenv("SPARK_OODA_INTERVAL_SECONDS", "60")))
