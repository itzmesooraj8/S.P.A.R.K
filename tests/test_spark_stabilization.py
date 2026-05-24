import unittest
from unittest.mock import patch, MagicMock
import os
import time

# Import targets
from audio.stt import SparkEars
from spark.voice import SparkVoice
from spark.llm import SparkLLM
from core.tools import SparkTools
from tools.browser import open_app, open_url
from core.spark_brain import _chat_completion, handle, GroqFallbackError, client
import groq
import httpx
import requests

class SparkStabilizationTests(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        # Reset environment or mocks if needed
        pass

    def test_whisper_stt_hallucination_filtering(self):
        ears = SparkEars()
        
        # Test blacklist filtering
        with patch("audio.stt.listen_and_transcribe", return_value="Thank you for watching."):
            self.assertIsNone(ears.listen())
            
        with patch("audio.stt.listen_and_transcribe", return_value="please subscribe"):
            self.assertIsNone(ears.listen())

        # Test length validation (default min length 3)
        with patch("audio.stt.listen_and_transcribe", return_value="ok"):
            self.assertIsNone(ears.listen())

        # Test valid transcription
        with patch("audio.stt.listen_and_transcribe", return_value="open notepad"):
            self.assertEqual(ears.listen(), "open notepad")

    def test_voice_listen_null_fallback(self):
        # SparkVoice should return "" when SparkEars returns None
        voice = SparkVoice({"voice": {"stt_seconds": 5}})
        with patch.object(voice.ears, "listen", return_value=None):
            self.assertEqual(voice.listen(), "")

        with patch.object(voice.ears, "listen", return_value="hello assistant"):
            self.assertEqual(voice.listen(), "hello assistant")

    def test_tools_open_app_redirection(self):
        tools = SparkTools()

        # Test type checking and cleaning dictation error "you tube" -> URL redirect
        with patch.object(tools, "open_website", return_value="MockWebOpen") as mock_web:
            res = tools.open_application("open you tube")
            mock_web.assert_called_with("open youtube")

        # Test URL structural checks
        with patch.object(tools, "open_website", return_value="MockWebOpen") as mock_web:
            tools.open_application("google.com")
            mock_web.assert_called_with("google.com")

        with patch.object(tools, "open_website", return_value="MockWebOpen") as mock_web:
            tools.open_application("https://github.com/issue")
            mock_web.assert_called_with("https://github.com/issue")

    def test_browser_open_app_redirection(self):
        # Test tools/browser.py open_app redirection
        with patch("tools.browser.open_url", return_value="MockBrowserOpen") as mock_url:
            res = open_app("you tube")
            mock_url.assert_called_with(url="https://youtube.com")

        with patch("tools.browser.open_url", return_value="MockBrowserOpen") as mock_url:
            res = open_app("google.com")
            mock_url.assert_called_with(url="google.com")

        def test_spark_llm_extract_tasks_handles_fenced_json(self):
                llm = SparkLLM({}, object(), {})
                payload = """```json
                [
                    {"prompt": "open the dashboard", "source": "user"}
                ]
                ```"""

                tasks = llm._extract_tasks(payload)

                self.assertEqual(tasks, [{"prompt": "open the dashboard", "source": "user"}])

    @patch("core.spark_brain.client")
    def test_groq_fallback_errors(self, mock_client):
        # Test low budget raising GroqFallbackError
        with patch("core.spark_brain.token_counter.get_remaining_today", return_value=1000):
            with self.assertRaises(GroqFallbackError):
                _chat_completion([{"role": "user", "content": "hi"}])

        # Test cooldown raising GroqFallbackError
        with patch("core.spark_brain._groq_cooldown_until", time.time() + 100):
            with self.assertRaises(GroqFallbackError):
                _chat_completion([{"role": "user", "content": "hi"}])

        # Test API connection error raising GroqFallbackError
        mock_client.chat.completions.create.side_effect = groq.APIConnectionError(
            message="Connection failed",
            request=MagicMock()
        )
        with patch("core.spark_brain.token_counter.get_remaining_today", return_value=50000):
            with patch("core.spark_brain._groq_cooldown_until", 0):
                with self.assertRaises(GroqFallbackError):
                    _chat_completion([{"role": "user", "content": "hi"}])

    @patch("core.spark_brain._chat_completion")
    @patch("core.spark_brain._local_chat_completion")
    async def test_handle_routes_to_local_on_fallback_error(self, mock_local_comp, mock_chat_comp):
        mock_chat_comp.side_effect = GroqFallbackError("Simulated fallback trigger")
        mock_local_comp.return_value = "Mocked local response"

        # Mocking external utilities to isolate execution
        with patch("core.spark_brain.memory.recall", return_value=[]), \
             patch("core.spark_brain.memory.store") as mock_store:
            
            res = await handle("test message", [])
            self.assertEqual(res["reply"], "Mocked local response")
            mock_local_comp.assert_called_once()

    @patch("core.spark_brain._chat_completion")
    @patch("core.spark_brain._local_chat_completion")
    async def test_handle_falls_back_when_multi_action_resolves_nothing(self, mock_local_comp, mock_chat_comp):
        mock_chat_comp.side_effect = GroqFallbackError("Simulated fallback trigger")
        mock_local_comp.return_value = "Fallback conversational reply"

        with patch("core.spark_brain.parse_intents", return_value=[
            MagicMock(action="respond"),
            MagicMock(action="respond"),
        ]), patch("core.spark_brain.memory.recall", return_value=[]), \
             patch("core.spark_brain.memory.store"):
            res = await handle("tell me about SPARK and how you learn", [])

        self.assertEqual(res["reply"], "Fallback conversational reply")
        mock_local_comp.assert_called()

    @patch("core.spark_brain._chat_completion")
    @patch("core.spark_brain._local_chat_completion")
    async def test_handle_rejects_malformed_tool_arguments(self, mock_local_comp, mock_chat_comp):
        mock_msg = MagicMock()
        mock_msg.refusal = None
        mock_tool_call = MagicMock()
        mock_tool_call.function = MagicMock(arguments="this is not valid json {")
        mock_tool_call.function.name = "web_search"
        mock_msg.tool_calls = [mock_tool_call]
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=mock_msg)]
        mock_chat_comp.return_value = mock_response

        with patch("core.spark_brain.memory.recall", return_value=[]), \
             patch("core.spark_brain.memory.store"):
            res = await handle("list files", [])
            
        self.assertEqual(res["tool_used"], "web_search")
        self.assertEqual(res["tool_result"], "Validation failed: tool_arguments_malformed")
        self.assertIn("malformed", res["reply"])

if __name__ == "__main__":
    unittest.main()
