from __future__ import annotations

import unittest

from security.schema_validator import validate_command_payload, validate_tool_arguments


class SchemaValidatorTests(unittest.TestCase):
    def test_validate_command_payload_extracts_text(self) -> None:
        result = validate_command_payload(
            {
                "module": "agent",
                "action": "message",
                "text": "  hello   spark  ",
                "context_snapshot": {"window": "Terminal"},
            }
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.cleaned_text, "hello spark")
        self.assertEqual(result.cleaned_payload["module"], "agent")
        self.assertEqual(result.cleaned_payload["action"], "message")
        self.assertEqual(result.cleaned_payload["context_snapshot"], {"window": "Terminal"})

    def test_validate_command_payload_rejects_overlong_text(self) -> None:
        result = validate_command_payload({"text": "a" * 2001})

        self.assertFalse(result.allowed)
        self.assertIn("intent_too_long", result.reasons)

    def test_validate_tool_arguments_parses_fenced_json(self) -> None:
        result = validate_tool_arguments(
            """```json
            {"query": "spark local architecture"}
            ```""",
            tool_name="web_search",
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.cleaned_payload["query"], "spark local architecture")

    def test_validate_tool_arguments_rejects_garbage(self) -> None:
        result = validate_tool_arguments("not json at all", tool_name="web_search")

        self.assertFalse(result.allowed)
        self.assertIn("tool_arguments_malformed", result.reasons)


if __name__ == "__main__":
    unittest.main()