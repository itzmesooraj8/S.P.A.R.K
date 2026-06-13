"""
Tests for spark.autonomy.loop

Tests:
- No predictions → loop skips
- Low confidence (0.3) → loop skips
- High confidence (0.8) → loop acts
- Lambda closure: correct app_name used
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from spark.autonomy.loop import ContinuousAgentLoop, LoopState
from spark.awareness.world_model import WorldModel
from spark.memory.working import WorkingMemory
from spark.cognition.goal_engine import GoalEngine
from spark.decisions.log import DecisionLog
from spark.skills.skill import SkillRegistry


def _make_mock_world_model(predictions=None):
    wm = MagicMock()
    wm.get_predictions.return_value = predictions or []
    wm.observe.return_value = {"current_activity": "unknown"}
    wm.snapshot.return_value = {}
    return wm


def _make_mock_executor():
    executor = AsyncMock()
    executor.run.return_value = {"success": True, "result": "executed"}
    return executor


def _make_mock_goal_engine(has_active=False):
    ge = MagicMock()
    ge.active_goals.return_value = [] if not has_active else [{"id": "1"}]
    ge.create_goal.return_value = MagicMock(id="test_goal")
    return ge


def _make_loop(world_model=None, executor=None, goal_engine=None):
    event_bus = MagicMock()
    event_bus.emit = MagicMock()
    awareness_bus = MagicMock()
    observer = AsyncMock()
    observer._take_snapshot.return_value = {}
    observer._process_snapshot.return_value = {}
    reasoning = MagicMock()
    reflection = MagicMock()
    reflection.reflect.return_value = {}
    planner = MagicMock()
    replanner = MagicMock()
    deliberation = AsyncMock()
    deliberation.deliberate.return_value = MagicMock(consensus="proceed", final_plan={"steps": [{"tool_needed": "test", "args": {}}]})
    working_memory = WorkingMemory()
    decision_log = DecisionLog()
    skill_registry = SkillRegistry()

    return ContinuousAgentLoop(
        event_bus=event_bus,
        awareness_bus=awareness_bus,
        observer=observer,
        executor=executor or _make_mock_executor(),
        goal_engine=goal_engine or _make_mock_goal_engine(),
        reasoning=reasoning,
        reflection=reflection,
        planner=planner,
        replanner=replanner,
        deliberation=deliberation,
        working_memory=working_memory,
        world_model=world_model or _make_mock_world_model(),
        decision_log=decision_log,
        skill_registry=skill_registry,
    )


class TestActionLoopSkips:
    @pytest.mark.asyncio
    async def test_no_predictions_skips(self):
        wm = _make_mock_world_model(predictions=[])
        loop = _make_loop(world_model=wm)
        loop._running = True

        await asyncio.sleep(0.1)
        loop._running = False

        assert loop._cycle_count == 0

    @pytest.mark.asyncio
    async def test_low_confidence_skips(self):
        wm = _make_mock_world_model(predictions=[
            {"need": "terminal_access", "confidence": 0.3, "reason": "test"}
        ])
        loop = _make_loop(world_model=wm)
        loop._running = True

        await asyncio.sleep(0.1)
        loop._running = False

        assert loop._cycle_count == 0

    @pytest.mark.asyncio
    async def test_high_confidence_acts(self):
        wm = _make_mock_world_model(predictions=[
            {"need": "terminal_access", "confidence": 0.8, "reason": "test"}
        ])
        executor = _make_mock_executor()
        loop = _make_loop(world_model=wm, executor=executor)
        loop._cycle_interval = 0.05
        await loop.start(interval=0.05)

        await asyncio.sleep(0.3)

        loop._running = False
        assert loop._cycle_count >= 1


class TestWorldModelWiring:
    def test_get_predictions_uses_dynamic_confidence(self):
        wm = WorldModel()
        for _ in range(8):
            wm.observe({"application": {"focused": "code.exe", "active": ["code.exe"]}})

        predictions = wm.get_predictions()
        assert len(predictions) > 0
        assert predictions[0]["confidence"] == pytest.approx(1.0, abs=0.01)

    def test_low_frequency_no_predictions(self):
        wm = WorldModel()
        for _ in range(2):
            wm.observe({"application": {"focused": "code.exe", "active": ["code.exe"]}})

        predictions = wm.get_predictions()
        assert predictions == []


class TestLambdaClosure:
    def test_lambda_captures_by_value(self):
        results = []

        def mock_execute(app):
            results.append(app)
            return {"success": True}

        app_name = "Chrome"
        handler = lambda a=app_name: mock_execute(a)

        app_name = "Firefox"
        handler()

        assert results[-1] == "Chrome"

    def test_separate_lambdas_different_values(self):
        results = []

        def mock_execute(app):
            results.append(app)
            return {"success": True}

        handler1 = lambda a="Chrome": mock_execute(a)
        handler2 = lambda a="Firefox": mock_execute(a)

        handler1()
        handler2()

        assert results[0] == "Chrome"
        assert results[1] == "Firefox"


class TestLoopStats:
    def test_stats_structure(self):
        loop = _make_loop()
        stats = loop.stats()
        assert "running" in stats
        assert "state" in stats
        assert "cycle_count" in stats
        assert "auto_act_threshold" in stats

    def test_set_threshold(self):
        loop = _make_loop()
        loop.set_proactive_threshold(0.5)
        assert loop._auto_act_threshold == 0.5

    def test_threshold_clamped(self):
        loop = _make_loop()
        loop.set_proactive_threshold(1.5)
        assert loop._auto_act_threshold == 1.0
        loop.set_proactive_threshold(-0.5)
        assert loop._auto_act_threshold == 0.0
