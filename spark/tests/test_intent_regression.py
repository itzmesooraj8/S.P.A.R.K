"""
Tests for spark.llm_router — Regression tests for intent classification.
"""

import pytest
from spark.llm_router import _classify_deterministic, classify_intent


class TestNewsClassification:
    def test_news_keywords_route_to_action(self):
        """'tell me about today news in india' must route to action_execution."""
        assert _classify_deterministic("tell me about today news in india") == "action_execution"

    def test_whatsapp_mention_routes_to_action(self):
        """'whatsapp tell me the latest' must route to action_execution."""
        assert _classify_deterministic("whatsapp tell me the latest") == "action_execution"

    def test_india_news_routes_to_action(self):
        """'provide me indian technology news' must route to action_execution."""
        assert _classify_deterministic("provide me indian technology news") == "action_execution"

    def test_latest_news_routes_to_action(self):
        """'latest news from india' must route to action_execution."""
        assert _classify_deterministic("latest news from india") == "action_execution"

    def test_what_happening_routes_to_action(self):
        """'what is happening in india' must route to action_execution."""
        assert _classify_deterministic("what is happening in india") == "action_execution"

    def test_tell_me_about_routes_to_action(self):
        """'tell me about technology' must route to action_execution."""
        assert _classify_deterministic("tell me about technology") == "action_execution"


class TestMemoryClassification:
    def test_remember_routes_to_memory(self):
        assert _classify_deterministic("remember this") == "memory_query"

    def test_what_did_i_say_routes_to_memory(self):
        assert _classify_deterministic("what did I say last time") == "memory_query"

    def test_my_name_routes_to_memory(self):
        assert _classify_deterministic("what is my name") == "memory_query"

    def test_my_favorite_routes_to_memory(self):
        assert _classify_deterministic("what is my favorite color") == "memory_query"


class TestGoalClassification:
    def test_create_goal_routes_to_goal(self):
        assert _classify_deterministic("create a goal to learn Python") == "goal_creation"

    def test_build_website_routes_to_goal(self):
        assert _classify_deterministic("build a website") == "goal_creation"


class TestActionClassification:
    def test_open_app_routes_to_action(self):
        assert _classify_deterministic("open notepad") == "action_execution"

    def test_search_routes_to_action(self):
        assert _classify_deterministic("search for python") == "action_execution"


class TestConversationClassification:
    def test_hello_routes_to_conversation(self):
        assert _classify_deterministic("hello how are you") == "conversation"

    def test_thanks_routes_to_conversation(self):
        assert _classify_deterministic("thank you") == "conversation"

    def test_who_are_you_routes_to_conversation(self):
        assert _classify_deterministic("who are you") == "conversation"


class TestTimeClassification:
    def test_what_time_routes_to_conversation(self):
        """Time is handled in conversation handler, not as separate intent."""
        assert _classify_deterministic("what time is it") == "conversation"

    def test_current_time_routes_to_conversation(self):
        assert _classify_deterministic("current time") == "conversation"
