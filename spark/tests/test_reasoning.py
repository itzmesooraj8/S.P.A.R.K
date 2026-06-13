"""
Tests for spark.cognition.reasoning

Tests:
- Deterministic fallback for scoring
- Deterministic fallback for synthesis
- Reasoning chain tracking
- Score clamping
"""

import pytest
from spark.cognition.reasoning import ReasoningEngine


class TestReasoningDeterministic:
    def test_score_option_returns_float(self):
        engine = ReasoningEngine()
        score = engine._score_option_deterministic("use Playwright", ["browser", "automation"], "web scraping")
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_score_increases_with_matching_criteria(self):
        engine = ReasoningEngine()
        score_match = engine._score_option_deterministic("browser automation", ["browser"], "context")
        score_no_match = engine._score_option_deterministic("file operations", ["browser"], "context")
        assert score_match > score_no_match

    def test_score_increases_with_context_match(self):
        engine = ReasoningEngine()
        score = engine._score_option_deterministic("option", ["browser"], "browser automation task")
        assert score > 0.5

    def test_score_clamped_at_1(self):
        engine = ReasoningEngine()
        score = engine._score_option_deterministic("browser browser", ["browser", "browser"], "browser browser browser")
        assert score <= 1.0

    def test_synthesize_deterministic(self):
        engine = ReasoningEngine()
        steps = [
            {"type": "fact", "content": "Python is popular"},
            {"type": "analysis", "content": "Analyzing: best language"},
        ]
        result = engine._synthesize_deterministic(steps, "best language")
        assert "Python" in result
        assert "best language" in result

    def test_synthesize_no_facts(self):
        engine = ReasoningEngine()
        steps = [{"type": "analysis", "content": "Analyzing"}]
        result = engine._synthesize_deterministic(steps, "question")
        assert "question" in result


class TestReasoningChain:
    def test_chain_tracking(self):
        engine = ReasoningEngine()
        engine.reason(context="ctx", question="q1")
        engine.reason(context="ctx", question="q2")
        chain = engine.recent_chain()
        assert len(chain) == 2
        assert chain[0]["question"] == "q1"
        assert chain[1]["question"] == "q2"

    def test_chain_limit(self):
        engine = ReasoningEngine()
        for i in range(15):
            engine.reason(context="ctx", question=f"q{i}")
        chain = engine.recent_chain(limit=5)
        assert len(chain) == 5

    def test_reason_returns_structure(self):
        engine = ReasoningEngine()
        result = engine.reason(context="test context", question="test question", facts=["fact1"])
        assert "question" in result
        assert "steps" in result
        assert "conclusion" in result
        assert len(result["steps"]) == 3


class TestDecide:
    def test_decide_returns_best(self):
        engine = ReasoningEngine()
        result = engine.decide(
            options=["option A", "option B"],
            criteria=["browser"],
            context="web task"
        )
        assert "best" in result
        assert "options" in result
        assert len(result["options"]) == 2

    def test_decide_scores_sorted(self):
        engine = ReasoningEngine()
        result = engine.decide(
            options=["browser automation", "file operations"],
            criteria=["browser"],
            context="web scraping"
        )
        scores = [o["score"] for o in result["options"]]
        assert scores == sorted(scores, reverse=True)

    def test_evaluate(self):
        engine = ReasoningEngine()
        result = engine.evaluate("open_app", "success")
        assert result["action"] == "open_app"
        assert result["outcome"] == "success"
