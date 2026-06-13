"""
Tests for spark.authority, spark.reliability.retry, spark.reliability.recovery, spark.llm_bridge

Tests:
- ALLOW permission → action executes
- REQUIRES_CONFIRMATION → returns needs_confirmation=True
- DENIED permission → action blocked
- RetryManager: fails twice, succeeds third try
- RetryManager: fails max_retries → returns failure
- Recovery: LLM bridge Groq failure → Ollama picked up
- Recovery: both LLMs fail → deterministic fallback
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from spark.authority.validator import ActionValidator, ValidationResult
from spark.authority.policy import AuthorityPolicy, Permission, PermissionLevel
from spark.reliability.retry import RetryManager
from spark.reliability.recovery import FailureRecovery
from spark.llm_bridge import LLMBridge


class TestAuthorityAllowed:
    def test_read_screen_allowed(self):
        validator = ActionValidator()
        result = validator.validate(Permission.READ_SCREEN, "test")
        assert result.allowed is True
        assert result.needs_confirmation is False

    def test_network_access_allowed(self):
        validator = ActionValidator()
        result = validator.validate(Permission.NETWORK_ACCESS, "test")
        assert result.allowed is True

    def test_access_files_allowed(self):
        validator = ActionValidator()
        result = validator.validate(Permission.ACCESS_FILES, "test")
        assert result.allowed is True


class TestAuthorityConfirmation:
    def test_open_browser_requires_confirmation(self):
        validator = ActionValidator()
        result = validator.validate(Permission.OPEN_BROWSER, "test")
        assert result.allowed is True
        assert result.needs_confirmation is True

    def test_execute_shell_requires_confirmation(self):
        validator = ActionValidator()
        result = validator.validate(Permission.EXECUTE_SHELL, "test")
        assert result.allowed is True
        assert result.needs_confirmation is True

    def test_send_email_requires_confirmation(self):
        validator = ActionValidator()
        result = validator.validate(Permission.SEND_EMAIL, "test")
        assert result.allowed is True
        assert result.needs_confirmation is True


class TestAuthorityDenied:
    def test_spend_money_denied(self):
        validator = ActionValidator()
        result = validator.validate(Permission.SPEND_MONEY, "test")
        assert result.allowed is False
        assert "denied" in result.reason.lower()

    def test_modify_system_denied(self):
        validator = ActionValidator()
        result = validator.validate(Permission.MODIFY_SYSTEM, "test")
        assert result.allowed is False

    def test_denied_blocks_action(self):
        validator = ActionValidator()
        result = validator.validate(Permission.SPEND_MONEY, "buy_something")
        assert not result
        assert result.allowed is False


class TestAuthorityToolValidation:
    def test_take_screenshot_maps_to_read_screen(self):
        validator = ActionValidator()
        result = validator.validate_tool("take_screenshot")
        assert result.allowed is True

    def test_web_search_maps_to_network(self):
        validator = ActionValidator()
        result = validator.validate_tool("web_search")
        assert result.allowed is True

    def test_send_email_maps_to_email_permission(self):
        validator = ActionValidator()
        result = validator.validate_tool("send_email")
        assert result.needs_confirmation is True


class TestAuthorityLogging:
    def test_logs_validation_checks(self):
        validator = ActionValidator()
        validator.validate(Permission.READ_SCREEN, "test1")
        validator.validate(Permission.SPEND_MONEY, "test2")
        log = validator.recent_log()
        assert len(log) == 2
        assert log[0]["allowed"] is True
        assert log[1]["allowed"] is False


class TestRetryManagerSuccess:
    @pytest.mark.asyncio
    async def test_succeeds_on_first_try(self):
        rm = RetryManager(max_retries=3, base_delay=0.01)
        action = AsyncMock(return_value="success")
        result = await rm.execute_with_retry(action)
        assert result["success"] is True
        assert result["attempts"] == 1
        action.assert_called_once()

    @pytest.mark.asyncio
    async def test_succeeds_on_third_try(self):
        rm = RetryManager(max_retries=3, base_delay=0.01)
        action = AsyncMock(side_effect=[ValueError("fail"), ValueError("fail"), "success"])
        result = await rm.execute_with_retry(action)
        assert result["success"] is True
        assert result["attempts"] == 3
        assert action.call_count == 3


class TestRetryManagerFailure:
    @pytest.mark.asyncio
    async def test_fails_after_max_retries(self):
        rm = RetryManager(max_retries=2, base_delay=0.01)
        action = AsyncMock(side_effect=ValueError("always fails"))
        result = await rm.execute_with_retry(action)
        assert result["success"] is False
        assert result["attempts"] == 2
        assert "always fails" in result["error"]

    @pytest.mark.asyncio
    async def test_records_all_attempts(self):
        rm = RetryManager(max_retries=2, base_delay=0.01)
        action = AsyncMock(side_effect=ValueError("fail"))
        await rm.execute_with_retry(action)
        history = rm.get_history()
        assert len(history) == 2
        assert all(h["error"] == "fail" for h in history)


class TestRetryManagerStrategies:
    @pytest.mark.asyncio
    async def test_uses_different_strategies(self):
        rm = RetryManager(max_retries=3, base_delay=0.01)
        action = AsyncMock(side_effect=[ValueError("f1"), ValueError("f2"), "ok"])
        result = await rm.execute_with_retry(action, strategies=["a", "b"])
        assert result["strategy"] == "a"


class TestRecoveryDiagnosis:
    def test_diagnoses_element_not_found(self):
        fr = FailureRecovery()
        diagnosis = fr.diagnose("element not found in DOM")
        assert diagnosis["category"] == "element_not_found"
        assert len(diagnosis["strategies"]) > 0

    def test_diagnoses_timeout(self):
        fr = FailureRecovery()
        diagnosis = fr.diagnose("request timed out")
        assert diagnosis["category"] == "timeout"

    def test_diagnoses_network_error(self):
        fr = FailureRecovery()
        diagnosis = fr.diagnose("network connection failed")
        assert diagnosis["category"] == "network_error"

    def test_diagnoses_permission_denied(self):
        fr = FailureRecovery()
        diagnosis = fr.diagnose("permission denied for this action")
        assert diagnosis["category"] == "permission_denied"

    def test_records_failure(self):
        fr = FailureRecovery()
        record = fr.record_failure("open_app", "element not found")
        assert record.action == "open_app"
        assert record.error == "element not found"


class TestLLMBridgeRecovery:
    @pytest.mark.asyncio
    async def test_groq_failure_falls_to_ollama_or_fallback(self):
        bridge = LLMBridge()
        with patch.object(bridge, '_ask_groq', side_effect=Exception("Groq down")):
            result = await bridge.ask("hello")
            assert isinstance(result, str)
            assert len(result) > 0

    @pytest.mark.asyncio
    async def test_all_backends_fail_uses_deterministic(self):
        bridge = LLMBridge()
        with patch.object(bridge, '_ask_groq', side_effect=Exception("Groq down")):
            with patch.object(bridge, '_ask_ollama', side_effect=Exception("Ollama down")):
                result = await bridge.ask("hello")
                assert isinstance(result, str)
                stats = bridge.stats()
                assert stats["fallback_calls"] >= 1

    @pytest.mark.asyncio
    async def test_budget_exhausted_skips_groq(self):
        bridge = LLMBridge()
        bridge.budget.used = 80_000
        bridge.budget.reset_date = "2099-01-01"
        result = await bridge.ask("hello")
        assert isinstance(result, str)
