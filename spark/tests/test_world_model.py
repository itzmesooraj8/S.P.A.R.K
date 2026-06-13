"""
Tests for spark.awareness.world_model

Tests:
- Dynamic confidence based on observation frequency
- No predictions with fewer than 3 observations
- Confidence scales with observation count
- Activity detection
"""

import pytest
from spark.awareness.world_model import WorldModel


def _make_observation(app: str, activity: str = "unknown") -> dict:
    return {
        "application": {"focused": app, "active": [app]},
    }


class TestDynamicConfidence:
    def test_no_predictions_below_3_observations(self):
        wm = WorldModel()
        wm.observe(_make_observation("code.exe"))
        wm.observe(_make_observation("code.exe"))
        predictions = wm._predict_needs("software_development", "code.exe")
        assert predictions == []

    def test_predictions_start_at_3_observations(self):
        wm = WorldModel()
        for _ in range(3):
            wm.observe(_make_observation("code.exe"))
        predictions = wm._predict_needs("software_development", "code.exe")
        assert len(predictions) > 0

    def test_confidence_scales_with_frequency(self):
        wm = WorldModel()
        for _ in range(8):
            wm.observe(_make_observation("code.exe"))
        for _ in range(2):
            wm.observe(_make_observation("chrome.exe"))
        predictions = wm._predict_needs("software_development", "code.exe")
        assert len(predictions) > 0
        assert predictions[0]["confidence"] == pytest.approx(0.8, abs=0.01)

    def test_low_frequency_below_threshold(self):
        wm = WorldModel()
        for _ in range(2):
            wm.observe(_make_observation("code.exe"))
        for _ in range(8):
            wm.observe(_make_observation("chrome.exe"))
        wm._current_activity = "software_development"
        predictions = wm._predict_needs("software_development", "code.exe")
        assert predictions == []

    def test_just_above_threshold(self):
        wm = WorldModel()
        for _ in range(3):
            wm.observe(_make_observation("code.exe"))
        for _ in range(7):
            wm.observe(_make_observation("chrome.exe"))
        wm._current_activity = "software_development"
        predictions = wm._predict_needs("software_development", "code.exe")
        assert len(predictions) > 0
        assert predictions[0]["confidence"] == pytest.approx(0.3, abs=0.01)

    def test_no_hardcoded_confidence_values(self):
        wm = WorldModel()
        for _ in range(10):
            wm.observe(_make_observation("code.exe"))
        predictions = wm._predict_needs("software_development", "code.exe")
        for p in predictions:
            assert p["confidence"] != 0.8
            assert p["confidence"] != 0.6
            assert p["confidence"] != 0.5

    def test_research_predictions(self):
        wm = WorldModel()
        for _ in range(5):
            wm.observe(_make_observation("chrome.exe"))
        predictions = wm._predict_needs("research", "chrome.exe")
        assert len(predictions) > 0
        assert predictions[0]["confidence"] > 0.3

    def test_communication_predictions(self):
        wm = WorldModel()
        for _ in range(5):
            wm.observe(_make_observation("discord.exe"))
        predictions = wm._predict_needs("communication", "discord.exe")
        assert len(predictions) > 0

    def test_unknown_activity_no_predictions(self):
        wm = WorldModel()
        for _ in range(5):
            wm.observe(_make_observation("random_app.exe"))
        predictions = wm._predict_needs("unknown", "random_app.exe")
        assert predictions == []


class TestActivityDetection:
    def test_detect_vscode(self):
        wm = WorldModel()
        result = wm.observe(_make_observation("code.exe"))
        assert result["current_activity"] == "software_development"

    def test_detect_browser(self):
        wm = WorldModel()
        result = wm.observe(_make_observation("chrome.exe"))
        assert result["current_activity"] == "research"

    def test_detect_discord(self):
        wm = WorldModel()
        result = wm.observe(_make_observation("discord.exe"))
        assert result["current_activity"] == "communication"

    def test_detect_unknown(self):
        wm = WorldModel()
        result = wm.observe(_make_observation("random_app.exe"))
        assert result["current_activity"] == "unknown"

    def test_current_activity_updates(self):
        wm = WorldModel()
        wm.observe(_make_observation("code.exe"))
        assert wm.get_current_activity() == "software_development"
        wm.observe(_make_observation("chrome.exe"))
        assert wm.get_current_activity() == "research"


class TestHabits:
    def test_tracks_app_usage(self):
        wm = WorldModel()
        wm.observe(_make_observation("code.exe"))
        wm.observe(_make_observation("code.exe"))
        habits = wm.get_habits()
        assert habits["frequent_apps"]["code.exe"] == 2
