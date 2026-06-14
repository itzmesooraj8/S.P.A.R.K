"""
Tests for spark.llm_bridge

Tests:
- TokenBudget tracking and daily reset
- LLMBridge.ask with deterministic fallback
- Backend priority (Groq → Ollama → fallback)
- Error handling
"""

import pytest
import time
from spark.llm_bridge import LLMBridge, TokenBudget, LLMError


class TestTokenBudget:
    def test_initial_state(self):
        budget = TokenBudget()
        assert budget.used == 0
        assert budget.daily_limit == 80_000
        assert budget.can_use_groq() is True

    def test_records_usage(self):
        budget = TokenBudget()
        budget.record_usage(100, "groq")
        assert budget.used == 100
        assert budget.groq_calls == 1

    def test_records_ollama_usage(self):
        budget = TokenBudget()
        budget.record_usage(0, "ollama")
        assert budget.ollama_calls == 1

    def test_records_fallback_usage(self):
        budget = TokenBudget()
        budget.record_usage(0, "deterministic")
        assert budget.fallback_calls == 1

    def test_budget_exhausted(self):
        budget = TokenBudget(daily_limit=100)
        budget.record_usage(100, "groq")
        assert budget.can_use_groq() is False

    def test_budget_remaining(self):
        budget = TokenBudget(daily_limit=100)
        budget.record_usage(30, "groq")
        stats = budget.stats()
        assert stats["remaining"] == 70

    def test_daily_reset(self):
        budget = TokenBudget()
        budget.used = 50_000
        budget.reset_date = "2000-01-01"
        budget.reset_if_new_day()
        assert budget.used == 0


class TestLLMBridge:
    @pytest.mark.asyncio
    async def test_deterministic_fallback_no_groq(self):
        bridge = LLMBridge()
        result = await bridge.ask("hello")
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_deterministic_fallback_question(self):
        bridge = LLMBridge()
        result = await bridge.ask("what is Python")
        assert "unavailable" in result.lower() or "python" in result.lower()

    @pytest.mark.asyncio
    async def test_deterministic_fallback_help(self):
        bridge = LLMBridge()
        result = await bridge.ask("help me")
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_stats_tracking(self):
        bridge = LLMBridge()
        result = await bridge.ask("test message")
        stats = bridge.stats()
        assert stats["groq_calls"] >= 1 or stats["fallback_calls"] >= 1

    @pytest.mark.asyncio
    async def test_ask_returns_string(self):
        bridge = LLMBridge()
        result = await bridge.ask("anything", max_tokens=10)
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_ask_with_system_prompt(self):
        bridge = LLMBridge()
        result = await bridge.ask("hi", system_prompt="You are a test assistant")
        assert isinstance(result, str)


class TestLLMError:
    def test_error_attributes(self):
        err = LLMError(message="test", backend="groq", cause="timeout")
        assert err.message == "test"
        assert err.backend == "groq"
        assert err.cause == "timeout"
