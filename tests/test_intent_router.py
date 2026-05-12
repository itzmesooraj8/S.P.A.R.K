from __future__ import annotations

import json
import unittest
from unittest.mock import patch

import intent_router


class IntentRouterTests(unittest.TestCase):
    def test_parse_intents_uses_groq_json(self):
        payload = {
            "tasks": [
                {"action": "open_app", "target": "discord", "params": {}},
                {"action": "open_app", "target": "brave", "params": {}},
                {"action": "open_url_in_browser", "target": "github", "params": {"browser": "chrome"}},
            ]
        }

        with patch.object(intent_router, "_call_groq_structured", return_value=json.dumps(payload)), \
             patch.object(intent_router, "_parse_with_local_hf", return_value=[]), \
             patch.object(intent_router, "_parse_with_regex", return_value=[]):
            tasks = intent_router.parse_intents("open discord and brave and search github in chrome")

        self.assertEqual(
            tasks,
            [
                intent_router.Task(action="open_app", target="discord", params={}),
                intent_router.Task(action="open_app", target="brave", params={}),
                intent_router.Task(action="open_url_in_browser", target="github", params={"browser": "chrome"}),
            ],
        )

    def test_parse_intents_falls_back_to_regex(self):
        with patch.object(intent_router, "_call_groq_structured", side_effect=intent_router.IntentRouterError("offline")), \
             patch.object(intent_router, "_parse_with_local_hf", return_value=[]):
            tasks = intent_router.parse_intents(
                "open microsoft store and discord and brave and spotify and in chrome open london map and in another tab search github"
            )

        self.assertEqual(
            [task.action for task in tasks],
            ["open_app", "open_app", "open_app", "open_app", "open_url_in_browser", "web_search"],
        )
        self.assertEqual(tasks[0].target, "microsoft store")
        self.assertEqual(tasks[-2].target, "london")
        self.assertEqual(tasks[-1].target, "github")
        self.assertEqual(tasks[-1].params.get("browser"), None)

    def test_local_model_loader_is_singleton(self):
        intent_router._LOCAL_MODEL = None
        calls = {"count": 0}

        def fake_loader():
            calls["count"] += 1
            return object()

        with patch.object(intent_router, "_load_local_model", side_effect=fake_loader):
            first = intent_router._get_local_model()
            second = intent_router._get_local_model()

        self.assertIs(first, second)
        self.assertEqual(calls["count"], 1)


if __name__ == "__main__":
    unittest.main()