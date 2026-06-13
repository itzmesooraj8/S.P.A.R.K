"""
Tests for spark.llm_router

Tests:
- Deterministic fallback for each intent
- Edge cases (empty input, punctuation)
- _validate_intent parsing
- Keyword coverage
"""

import pytest
from spark.llm_router import classify_intent, _classify_deterministic, _validate_intent, INTENTS


class TestValidateIntent:
    def test_exact_match(self):
        assert _validate_intent("goal_creation") == "goal_creation"
        assert _validate_intent("action_execution") == "action_execution"
        assert _validate_intent("memory_query") == "memory_query"
        assert _validate_intent("status_check") == "status_check"
        assert _validate_intent("conversation") == "conversation"

    def test_strips_punctuation(self):
        assert _validate_intent("goal_creation.") == "goal_creation"
        assert _validate_intent("'action_execution'") == "action_execution"
        assert _validate_intent('"memory_query"') == "memory_query"

    def test_case_insensitive(self):
        assert _validate_intent("Goal_Creation") == "goal_creation"
        assert _validate_intent("ACTION_EXECUTION") == "action_execution"

    def test_partial_match(self):
        assert _validate_intent("I think goal_creation is right") == "goal_creation"

    def test_invalid_returns_none(self):
        assert _validate_intent("completely unrelated") is None
        assert _validate_intent("") is None


class TestDeterministicClassification:
    def test_goal_creation(self):
        assert _classify_deterministic("create a goal to learn Python") == "goal_creation"
        assert _classify_deterministic("plan my week") == "goal_creation"
        assert _classify_deterministic("build a website") == "goal_creation"
        assert _classify_deterministic("I want to achieve something") == "goal_creation"

    def test_action_execution(self):
        assert _classify_deterministic("open VS Code") == "action_execution"
        assert _classify_deterministic("search for Python docs") == "action_execution"
        assert _classify_deterministic("run the tests") == "action_execution"
        assert _classify_deterministic("launch Chrome") == "action_execution"
        assert _classify_deterministic("find my notes") == "action_execution"

    def test_memory_query(self):
        assert _classify_deterministic("remember this") == "memory_query"
        assert _classify_deterministic("what did I say last time") == "memory_query"
        assert _classify_deterministic("recall our conversation") == "memory_query"

    def test_status_check(self):
        assert _classify_deterministic("show me the dashboard") == "status_check"
        assert _classify_deterministic("system health") == "status_check"
        assert _classify_deterministic("how are things") == "status_check"

    def test_conversation_fallback(self):
        assert _classify_deterministic("hello") == "conversation"
        assert _classify_deterministic("what is the weather") == "conversation"
        assert _classify_deterministic("tell me a joke") == "conversation"


class TestClassifyIntent:
    @pytest.mark.asyncio
    async def test_empty_input(self):
        result = await classify_intent("")
        assert result == "conversation"

    @pytest.mark.asyncio
    async def test_whitespace_input(self):
        result = await classify_intent("   ")
        assert result == "conversation"

    @pytest.mark.asyncio
    async def test_deterministic_fallback(self):
        result = await classify_intent("open Chrome browser")
        assert result == "action_execution"

    @pytest.mark.asyncio
    async def test_goal_keywords(self):
        result = await classify_intent("build a personal website")
        assert result == "goal_creation"

    @pytest.mark.asyncio
    async def test_memory_keywords(self):
        result = await classify_intent("remember my password")
        assert result == "memory_query"

    @pytest.mark.asyncio
    async def test_status_keywords(self):
        result = await classify_intent("show system status")
        assert result == "status_check"

    @pytest.mark.asyncio
    async def test_conversation_keywords(self):
        result = await classify_intent("tell me a joke")
        assert result == "conversation"


class TestIntentLabels:
    def test_all_intents_are_valid_strings(self):
        for intent in INTENTS:
            assert isinstance(intent, str)
            assert "_" in intent or intent == "conversation"

    def test_exactly_five_intents(self):
        assert len(INTENTS) == 5
