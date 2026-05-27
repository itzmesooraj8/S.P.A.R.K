# tests/test_hud_integration.py
import unittest
import asyncio
import os
import shutil
import json
from unittest.mock import patch, MagicMock
from security.intent_validator import clean_conversational_filler
from core.model_router import validate_model
from core.spark_brain import _chat_completion, GroqFallbackError
from core.workspace_generator import verify_safe_path
from security.defense_interceptor import secure_generate_workspace as generate_workspace
from api.server import VitalsWebSocketRouter

class TestHUDIntegration(unittest.TestCase):
    def test_intent_sanitization(self):
        """1. Assert conversational fillers are iteratively stripped."""
        inputs = {
            "alright no but listen, open notepad": "open notepad",
            "start creating for me, build a website": "build a website",
            "please build a clinic app": "build a clinic app",
            "gently create a file": "create a file",
            "okay so now search google": "search google",
            "hey spark, open chrome": "open chrome",
        }
        for raw, expected in inputs.items():
            cleaned = clean_conversational_filler(raw)
            self.assertEqual(cleaned, expected, f"Failed on raw input: {raw}")

    def test_model_validation(self):
        """2. Assert whitelisting behavior in model_router."""
        # Whitelisted models
        self.assertTrue(validate_model("llama-3.3-70b-versatile"))
        self.assertTrue(validate_model("qwen2.5:7b"))
        self.assertTrue(validate_model("gemma4"))
        
        # Invalid model
        self.assertFalse(validate_model("gemma3:4b"))
        self.assertFalse(validate_model("invalid_model_123"))

    @patch("core.spark_brain.client")
    @patch("core.model_router.get_groq_model")
    def test_invalid_model_fails_validation_instantly(self, mock_get_model, mock_client):
        """3. Assert validation failure raises GroqFallbackError before API call."""
        mock_get_model.return_value = "gemma3:4b" # Invalid
        
        with self.assertRaises(GroqFallbackError) as context:
            _chat_completion([{"role": "user", "content": "hello"}], allow_tools=False)
            
        self.assertIn("Model validation failed", str(context.exception))
        # Verify groq client was never invoked
        mock_client.chat.completions.create.assert_not_called()

    @patch("core.spark_brain.client", None)
    @patch("core.spark_brain._local_chat_completion")
    @patch("security.defense_interceptor.DefensiveInterceptor.pre_flight_checks")
    def test_workspace_generator_manifest(self, mock_preflight, mock_local_comp):
        """4. Assert manifest workspace generator parses and writes sandboxed files."""
        mock_preflight.return_value = True
        # Clean sandbox test area
        test_proj = "test_healthcare_portal"
        proj_dir = os.path.join("sandbox", test_proj)
        if os.path.exists(proj_dir):
            shutil.rmtree(proj_dir)
            
        mock_manifest = {
            "project_name": test_proj,
            "frameworks": ["bootstrap"],
            "block_locations": {"header": "header block", "content": "main portal", "footer": "foot block"},
            "view_parameters": {"theme": "dark", "viewport": "width=device-width"},
            "files": [
                {
                    "path": "index.html",
                    "content": "<html><body><h1>Healthcare Portal</h1></body></html>"
                },
                {
                    "path": "style.css",
                    "content": "body { color: blue; }"
                }
            ]
        }
        
        mock_local_comp.return_value = f"```json\n{json.dumps(mock_manifest)}\n```"
        
        # Run generator
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(generate_workspace(test_proj, "build a healthcare app"))
        finally:
            loop.close()
            
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["project_name"], test_proj)
        
        # Verify files are physically written under sandbox/test_healthcare_portal/
        self.assertTrue(os.path.exists(os.path.join(proj_dir, "index.html")))
        self.assertTrue(os.path.exists(os.path.join(proj_dir, "style.css")))
        
        # Verify path traversal protection
        with self.assertRaises(PermissionError):
            verify_safe_path("../traversal_attempt.html")
            
        # Clean up
        if os.path.exists(proj_dir):
            shutil.rmtree(proj_dir)

    def test_vitals_router_daemon_loop(self):
        """5. Assert VitalsWebSocketRouter background daemon updates metrics."""
        router = VitalsWebSocketRouter()
        self.assertFalse(router._running)
        router.start_daemon()
        self.assertTrue(router._running)
        
        # Wait a short moment for the daemon to run at least one tick
        import time
        time.sleep(0.3)
        
        metrics = router.get_metrics()
        self.assertIn("cpu", metrics)
        self.assertIn("ramFree", metrics)
        self.assertIn("ramTotal", metrics)
        self.assertIn("batteryPercent", metrics)
        
        router.stop_daemon()
        time.sleep(0.1)

if __name__ == "__main__":
    unittest.main()
