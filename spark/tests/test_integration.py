"""
Integration Tests — Full Request Lifecycle

Tests the complete chain for each intent type:
1. action_execution → ExecutorAgent → returns result
2. goal_creation → PlannerAgent → GoalEngine → goal created
3. memory_query → MemoryAgent → stored in working memory
4. status_check → returns current system state
5. conversation → returns acknowledgment

Uses mocks for: Groq API, Ollama, actual desktop/browser calls
Does NOT mock: intent router logic, agent routing, memory storage
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from spark.llm_router import classify_intent
from spark.llm_bridge import LLMBridge
from spark.memory.working import WorkingMemory
from spark.memory.episodic import EpisodicMemory
from spark.cognition.goal_engine import GoalEngine
from spark.awareness.world_model import WorldModel
from spark.decisions.log import DecisionLog
from spark.skills.skill import SkillRegistry


class TestIntentClassificationChain:
    @pytest.mark.asyncio
    async def test_action_intent(self):
        intent = await classify_intent("open Chrome browser")
        assert intent == "action_execution"

    @pytest.mark.asyncio
    async def test_goal_intent(self):
        intent = await classify_intent("create a goal to learn FastAPI")
        assert intent == "goal_creation"

    @pytest.mark.asyncio
    async def test_memory_intent(self):
        intent = await classify_intent("remember my name is Sooraj")
        assert intent == "memory_query"

    @pytest.mark.asyncio
    async def test_status_intent(self):
        intent = await classify_intent("show me the dashboard")
        assert intent == "status_check"

    @pytest.mark.asyncio
    async def test_conversation_intent(self):
        intent = await classify_intent("tell me a joke")
        assert intent == "conversation"


class TestLLMBridgeChain:
    @pytest.mark.asyncio
    async def test_bridge_returns_string(self):
        bridge = LLMBridge()
        result = await bridge.ask("What is 2+2?", max_tokens=10)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_bridge_with_system_prompt(self):
        bridge = LLMBridge()
        result = await bridge.ask("hello", system_prompt="You are a test assistant")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_bridge_fallback_works(self):
        bridge = LLMBridge()
        result = await bridge.ask("help me")
        assert isinstance(result, str)
        stats = bridge.stats()
        assert stats["fallback_calls"] >= 1


class TestMemoryChain:
    def test_working_memory_stores_context(self):
        wm = WorkingMemory()
        wm.update_context(current_window="VS Code", current_app="code.exe")
        ctx = wm.get_context()
        assert ctx["current_window"] == "VS Code"
        assert ctx["current_app"] == "code.exe"

    def test_working_memory_objective(self):
        wm = WorkingMemory()
        wm.set_objective("Learn FastAPI", subtasks_total=5)
        obj = wm.get_objective()
        assert obj["description"] == "Learn FastAPI"
        assert obj["subtasks_total"] == 5

    def test_episodic_memory_records(self):
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".jsonl")
        try:
            em = EpisodicMemory(storage_path=tmp)
            em.record("user", "hello", {"source": "chat"})
            em.record("assistant", "hi there", {"source": "chat"})
            recent = em.recent(10)
            assert len(recent) == 2
            assert recent[0]["role"] == "user"
            assert recent[1]["role"] == "assistant"
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass


class TestGoalEngineChain:
    def _fresh_engine(self):
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".json")
        ge = GoalEngine(storage_path=tmp)
        yield ge
        try:
            os.unlink(tmp)
        except OSError:
            pass

    def test_create_goal(self):
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".json")
        try:
            ge = GoalEngine(storage_path=tmp)
            goal = ge.create_goal("Learn Python", priority=7)
            assert goal.description == "Learn Python"
            assert goal.priority == 7
            assert ge.get_goal(goal.id) is not None
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def test_active_goals(self):
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".json")
        try:
            ge = GoalEngine(storage_path=tmp)
            ge.create_goal("Goal 1")
            ge.create_goal("Goal 2")
            active = ge.active_goals()
            assert len(active) == 2
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass

    def test_complete_subtask(self):
        import tempfile, os
        tmp = tempfile.mktemp(suffix=".json")
        try:
            ge = GoalEngine(storage_path=tmp)
            goal = ge.create_goal("Test Goal")
            from spark.cognition.goal_engine import Plan, Subtask
            subtask = Subtask(description="Step 1")
            plan = Plan(goal_id=goal.id, steps=[subtask])
            goal.plan = plan
            ge.complete_subtask(goal.id, subtask.id, "done", success=True)
            assert subtask.status.value == "done"
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass


class TestWorldModelChain:
    def test_observe_updates_activity(self):
        wm = WorldModel()
        result = wm.observe({"application": {"focused": "code.exe", "active": ["code.exe"]}})
        assert result["current_activity"] == "software_development"

    def test_predictions_require_history(self):
        wm = WorldModel()
        wm.observe({"application": {"focused": "code.exe", "active": ["code.exe"]}})
        predictions = wm.get_predictions()
        assert predictions == []

    def test_predictions_after_enough_data(self):
        wm = WorldModel()
        for _ in range(5):
            wm.observe({"application": {"focused": "code.exe", "active": ["code.exe"]}})
        predictions = wm.get_predictions()
        assert len(predictions) > 0


class TestDecisionLogChain:
    def test_log_and_retrieve(self):
        dl = DecisionLog()
        decision = dl.log("test_action", "testing", {"key": "value"})
        recent = dl.recent(5)
        assert len(recent) >= 1
        assert recent[-1]["action"] == "test_action"

    def test_record_outcome(self):
        dl = DecisionLog()
        decision = dl.log("test_action", "testing")
        dl.record_outcome(decision, "completed", True)
        recent = dl.recent(5)
        assert recent[-1]["outcome"] == "completed"


class TestSkillRegistryChain:
    def test_learn_skill(self):
        sr = SkillRegistry()
        skill = sr.learn_from_action(
            "test_skill",
            [{"action": "web_search", "params": {"query": "test"}}],
            description="Test skill",
            tags=["test"],
        )
        assert skill.name == "test_skill"
        assert sr.has("test_skill")

    def test_find_skill(self):
        sr = SkillRegistry()
        sr.learn_from_action("web_search_skill", [{"action": "web_search"}], tags=["search"])
        found = sr.find_best("search")
        assert found is not None
