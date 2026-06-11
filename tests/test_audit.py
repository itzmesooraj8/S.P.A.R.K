import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from security.audit import get_recent_audit, record_audit


class SecurityAuditTests(unittest.TestCase):
    def test_record_and_read_recent_audit_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "security_audit.jsonl"
            with patch.dict(os.environ, {"SPARK_SECURITY_AUDIT_LOG": str(audit_path)}, clear=False):
                first = record_audit("auth_login_success", {"username": "operator"})
                second = record_audit("auth_logout", {"username": "operator"})

                self.assertTrue(audit_path.exists())
                recent = get_recent_audit(limit=1)

                self.assertEqual(recent, [second])
                self.assertNotEqual(first["id"], second["id"])

    def test_audit_redacts_sensitive_payload_values(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            audit_path = Path(tmpdir) / "security_audit.jsonl"
            with patch.dict(os.environ, {"SPARK_SECURITY_AUDIT_LOG": str(audit_path)}, clear=False):
                record_audit(
                    "auth_login_rejected",
                    {
                        "username": "operator",
                        "password": "do-not-log",
                        "nested": {"refresh_token": "also-secret"},
                    },
                )

                line = audit_path.read_text(encoding="utf-8").strip()
                event = json.loads(line)

                self.assertEqual(event["payload"]["username"], "operator")
                self.assertEqual(event["payload"]["password"], "[redacted]")
                self.assertEqual(event["payload"]["nested"]["refresh_token"], "[redacted]")


if __name__ == "__main__":
    unittest.main()
