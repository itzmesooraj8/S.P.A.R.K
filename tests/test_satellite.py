import unittest
import time
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from api.server import app
from security.signature_verifier import (
    generate_signature,
    verify_signature,
    verify_remote_request,
    canonical_serialize,
    get_secret_key
)

class SatelliteSecureTests(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        self.secret_key = get_secret_key()

    def test_canonical_serialize_ordering(self):
        payload1 = {"text": "hello", "timestamp": 12345.6}
        payload2 = {"timestamp": 12345.6, "text": "hello"}
        self.assertEqual(canonical_serialize(payload1), canonical_serialize(payload2))

    def test_verify_signature_correct(self):
        payload = {"text": "hello", "timestamp": time.time()}
        sig = generate_signature(payload, self.secret_key)
        self.assertTrue(verify_signature(payload, sig, self.secret_key))

    def test_verify_signature_incorrect(self):
        payload = {"text": "hello", "timestamp": time.time()}
        self.assertFalse(verify_signature(payload, "invalid-sig", self.secret_key))

    def test_verify_remote_request_drift_valid(self):
        payload = {"text": "hello", "timestamp": time.time()}
        sig = generate_signature(payload, self.secret_key)
        self.assertTrue(verify_remote_request(payload, sig))

    def test_verify_remote_request_drift_invalid(self):
        payload = {"text": "hello", "timestamp": time.time() - 400}
        sig = generate_signature(payload, self.secret_key)
        self.assertFalse(verify_remote_request(payload, sig))

    def test_satellite_endpoint_unauthorized(self):
        payload = {"text": "hello", "timestamp": time.time()}
        response = self.client.post(
            "/api/satellite/command",
            json={
                "payload": payload,
                "signature": "invalid-signature"
            }
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"error": "unauthorized"})

    @patch("api.routes.satellite.ask_spark_brain")
    def test_satellite_endpoint_authorized(self, mock_ask):
        mock_ask.return_value = {
            "reply": "Acknowledged, sir.",
            "tool_used": "get_time",
            "tool_result": "12:00 PM"
        }
        
        payload = {"text": "what time is it", "timestamp": time.time()}
        sig = generate_signature(payload, self.secret_key)
        
        # Mock edge_tts Communicate to avoid network activity during test
        with patch("edge_tts.Communicate") as mock_comm:
            mock_comm.return_value.save = MagicMock()
            response = self.client.post(
                "/api/satellite/command",
                json={
                    "payload": payload,
                    "signature": sig
                }
            )
        
        self.assertEqual(response.status_code, 200)
        json_resp = response.json()
        self.assertEqual(json_resp["reply"], "Acknowledged, sir.")
        self.assertEqual(json_resp["tool_used"], "get_time")
        self.assertEqual(json_resp["tool_result"], "12:00 PM")

if __name__ == "__main__":
    unittest.main()
