"""Continuous Agent Loop — The brain that never stops.

Observe → Understand → Predict → Plan → Act → Reflect → Learn → Observe

Forever. 24/7.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

from spark.core.events import EventBus
from spark.awareness.bus import AwarenessBus
from spark.awareness.world_model import WorldModel
from spark.memory.working import WorkingMemory
from spark.cognition.goal_engine import GoalEngine
from spark.cognition.reasoning import ReasoningEngine
from spark.cognition.reflection import ReflectionEngine
from spark.planning.llm_planner import LLMPlanner
from spark.planning.replanner import AutoReplanner
from spark.planning.deliberation import MultiAgentDeliberation
from spark.agents.executor import ExecutorAgent
from spark.agents.observer import ObserverAgent
from spark.decisions.log import DecisionLog
from spark.skills.skill import SkillRegistry

logger = logging.getLogger("spark.autonomy.loop")


class LoopState:
    IDLE = "idle"
    OBSERVING = "observing"
    UNDERSTANDING = "understanding"
    PREDICTING = "predicting"
    PLANNING = "planning"
    ACTING = "acting"
    REFLECTING = "reflecting"
    LEARNING = "learning"


class ContinuousAgentLoop:
    """
    The brain that never stops.

    Runs the full autonomous loop:
    1. Observe — take snapshot of environment
    2. Understand — analyze what's happening (world model)
    3. Predict — what will user likely need
    4. Plan — create plan for predicted needs
    5. Act — execute plan (with authority checks)
    6. Reflect — analyze what happened
    7. Learn — update skills and strategies
    8. Observe — repeat forever

    This is what separates an assistant from an operating system.
    """

    def __init__(
        self,
        event_bus: EventBus,
        awareness_bus: AwarenessBus,
        observer: ObserverAgent,
        executor: ExecutorAgent,
        goal_engine: GoalEngine,
        reasoning: ReasoningEngine,
        reflection: ReflectionEngine,
        planner: LLMPlanner,
        replanner: AutoReplanner,
        deliberation: MultiAgentDeliberation,
        working_memory: WorkingMemory,
        world_model: WorldModel,
        decision_log: DecisionLog,
        skill_registry: SkillRegistry,
    ) -> None:
        self._event_bus = event_bus
        self._awareness_bus = awareness_bus
        self._observer = observer
        self._executor = executor
        self._goal_engine = goal_engine
        self._reasoning = reasoning
        self._reflection = reflection
        self._planner = planner
        self._replanner = replanner
        self._deliberation = deliberation
        self._working_memory = working_memory
        self._world_model = world_model
        self._decision_log = decision_log
        self._skill_registry = skill_registry

        self._state = LoopState.IDLE
        self._running = False
        self._cycle_count = 0
        self._last_cycle = 0.0
        self._cycle_interval = 5.0
        self._auto_act_threshold = 0.7
        self._on_proactive_action: Callable | None = None
        self._cycle_log: list[dict[str, Any]] = []

    async def start(self, interval: float | None = None) -> None:
        """Start the continuous loop."""
        self._running = True
        self._cycle_interval = interval or self._cycle_interval
        logger.info("Continuous Agent Loop started (interval: %.1fs)", self._cycle_interval)

        asyncio.create_task(self._observation_loop())
        asyncio.create_task(self._action_loop())

    def stop(self) -> None:
        self._running = False
        logger.info("Continuous Agent Loop stopped")

    async def _observation_loop(self) -> None:
        """Continuous observation — always watching."""
        while self._running:
            try:
                self._state = LoopState.OBSERVING
                snapshot = await self._observer._take_snapshot()
                await self._observer._process_snapshot(snapshot)

                self._state = LoopState.UNDERSTANDING
                world_update = self._world_model.observe(snapshot)
                self._working_memory.update_context(**snapshot.get("context", {}))

                self._state = LoopState.PREDICTING
                predictions = self._world_model.get_predictions()
                self._working_memory.set_attention(
                    focus=predictions[0].get("need", "") if predictions else "",
                    priority=8 if predictions else 3,
                )

                self._event_bus.emit("loop.observation", {
                    "cycle": self._cycle_count,
                    "world_model": world_update,
                    "predictions": predictions,
                })

            except Exception as exc:
                logger.error("Observation loop error: %s", exc)

            await asyncio.sleep(self._cycle_interval)

    async def _action_loop(self) -> None:
        """Continuous action — proactively acts on predictions."""
        while self._running:
            try:
                await asyncio.sleep(self._cycle_interval * 2)

                if self._state == LoopState.OBSERVING:
                    continue

                self._cycle_count += 1
                self._last_cycle = time.time()

                predictions = self._world_model.get_predictions()
                if not predictions:
                    continue

                top_prediction = predictions[0]
                if top_prediction.get("confidence", 0) < self._auto_act_threshold:
                    continue

                if self._goal_engine.active_goals():
                    continue

                self._state = LoopState.PLANNING
                decision = self._decision_log.log(
                    "proactive_action",
                    f"Predicted need: {top_prediction.get('need', '?')} (confidence: {top_prediction.get('confidence', 0):.0%})",
                    {"prediction": top_prediction},
                )

                goal = self._goal_engine.create_goal(
                    f"Address predicted need: {top_prediction.get('need', '?')}",
                    priority=4,
                    metadata={"source": "proactive", "prediction": top_prediction},
                )

                plan_result = await self._deliberation.deliberate(
                    goal.description,
                    context={"prediction": top_prediction, "world_model": self._world_model.snapshot()},
                )

                if plan_result.consensus == "proceed":
                    self._state = LoopState.ACTING
                    task = {
                        "description": goal.description,
                        "tool_needed": plan_result.final_plan.get("steps", [{}])[0].get("tool_needed"),
                        "args": plan_result.final_plan.get("steps", [{}])[0].get("args", {}),
                    }
                    result = await self._executor.run(task=task)

                    self._state = LoopState.REFLECTING
                    reflection = self._reflection.reflect(
                        [{"tool": task.get("tool_needed"), "success": result.get("success", False), "result": str(result)[:100]}],
                        context={"prediction": top_prediction},
                    )

                    self._state = LoopState.LEARNING
                    if result.get("success"):
                        self._skill_registry.learn_from_action(
                            f"proactive_{top_prediction.get('need', 'unknown')}",
                            [{"action": task.get("tool_needed", ""), "params": task.get("args", {})}],
                            description=f"Proactive action for: {top_prediction.get('need', '?')}",
                            tags=["proactive", top_prediction.get("need", "")],
                        )

                    self._decision_log.record_outcome(decision, "proactive_executed", result.get("success", False))

                cycle_entry = {
                    "cycle": self._cycle_count,
                    "prediction": top_prediction,
                    "consensus": plan_result.consensus,
                    "timestamp": time.time(),
                }
                self._cycle_log.append(cycle_entry)
                if len(self._cycle_log) > 100:
                    self._cycle_log = self._cycle_log[-100:]

                self._state = LoopState.IDLE

            except Exception as exc:
                logger.error("Action loop error: %s", exc)
                self._state = LoopState.IDLE

    def set_proactive_threshold(self, threshold: float) -> None:
        self._auto_act_threshold = max(0.0, min(1.0, threshold))

    def on_proactive_action(self, handler: Callable) -> None:
        self._on_proactive_action = handler

    def state(self) -> str:
        return self._state

    def stats(self) -> dict[str, Any]:
        return {
            "running": self._running,
            "state": self._state,
            "cycle_count": self._cycle_count,
            "last_cycle": self._last_cycle,
            "auto_act_threshold": self._auto_act_threshold,
            "recent_cycles": self._cycle_log[-10:],
        }
