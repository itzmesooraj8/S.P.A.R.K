"""Unit and Integration Tests for S.P.A.R.K. WebSockets Security and Tool RBAC.

Validates that unauthorized WebSocket connections are rejected, and that
fine-grained tool-level RBAC rules are enforced via context variables.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.auth import issue_token_pair
from api.server import app
from security.session_authorization import (
    active_user_var,
    authorize_sensitive_tool,
    validate_session_auth,
)
from security.user_db import UserDatabaseManager


class WebSocketAndToolSecurityTests(unittest.TestCase):

    def setUp(self):
        # Configure temporary test user DB
        from security.user_db import user_db_manager
        self.original_db_path = user_db_manager.db_path
        self.test_db_path = "knowledge_base/test_ws_security.db"
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass
        user_db_manager.db_path = self.test_db_path
        user_db_manager._init_db()
        self.db = user_db_manager
        self.client = TestClient(app)

    def tearDown(self):
        from security.user_db import user_db_manager
        self.db.close()
        user_db_manager.db_path = self.original_db_path
        user_db_manager._init_db()
        if os.path.exists(self.test_db_path):
            try:
                os.remove(self.test_db_path)
            except OSError:
                pass

    # --- 1. WebSocket Authorization Tests ---
    def test_websocket_vitals_unauthorized_rejected(self):
        # Attempt connecting to `/ws/vitals` without token
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/vitals") as ws:
                pass

    def test_websocket_ai_unauthorized_rejected(self):
        # Attempt connecting to `/ws/ai` without token
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/ai") as ws:
                pass

    def test_websocket_ai_authorized_accepted(self):
        # 1. Create a user
        self.db.create_user("operator_bob", "password123", role="operator", permissions=["chat", "tools"])
        user_dto = self.db.authenticate_user("operator_bob", "password123")
        self.assertIsNotNone(user_dto)

        # 2. Issue token
        from api.auth import AuthenticatedUser
        user = AuthenticatedUser(username="operator_bob", role="operator", permissions=["chat", "tools"])
        tokens = issue_token_pair(user)

        # 3. Connect to WebSocket with token parameter
        with self.client.websocket_connect(f"/ws/ai?token={tokens.access_token}") as ws:
            # Send an empty or cancel packet to verify it is responsive and connection stayed open
            ws.send_json({"type": "CANCEL"})
            response = ws.receive_json()
            self.assertEqual(response["type"], "ERROR")
            self.assertIn("cancelled", response["code"])

    # --- 2. Tool-Level RBAC Enforcements ---
    def test_tool_rbac_viewer_blocked_from_admin_tool(self):
        user_ctx = {"username": "alice_viewer", "role": "viewer", "permissions": ["chat"]}
        token = active_user_var.set(user_ctx)
        try:
            # execute_python is admin-only tool
            auth_res = authorize_sensitive_tool("execute_python", {"code": "print(1)"})
            self.assertFalse(auth_res.allowed)
            self.assertEqual(auth_res.reason, "admin_role_required")
        finally:
            active_user_var.reset(token)

    def test_tool_rbac_viewer_blocked_from_operator_tool(self):
        user_ctx = {"username": "alice_viewer", "role": "viewer", "permissions": ["chat"]}
        token = active_user_var.set(user_ctx)
        try:
            # control_device is operator-level tool
            auth_res = authorize_sensitive_tool("control_device", {"device": "fan", "action": "on"})
            self.assertFalse(auth_res.allowed)
            self.assertEqual(auth_res.reason, "operator_role_required")
        finally:
            active_user_var.reset(token)

    def test_tool_rbac_operator_allowed_for_operator_tool(self):
        user_ctx = {"username": "bob_operator", "role": "operator", "permissions": ["chat", "tools"]}
        token = active_user_var.set(user_ctx)
        try:
            # control_device is operator-level tool
            auth_res = authorize_sensitive_tool("control_device", {"device": "fan", "action": "on"})
            self.assertTrue(auth_res.allowed)
        finally:
            active_user_var.reset(token)

    def test_tool_rbac_operator_blocked_from_admin_tool(self):
        user_ctx = {"username": "bob_operator", "role": "operator", "permissions": ["chat", "tools"]}
        token = active_user_var.set(user_ctx)
        try:
            # execute_python is admin-only tool
            auth_res = authorize_sensitive_tool("execute_python", {"code": "print(1)"})
            self.assertFalse(auth_res.allowed)
            self.assertEqual(auth_res.reason, "admin_role_required")
        finally:
            active_user_var.reset(token)

    def test_tool_rbac_admin_allowed_for_all_tools(self):
        user_ctx = {"username": "charlie_admin", "role": "admin", "permissions": ["chat", "tools", "admin"]}
        token = active_user_var.set(user_ctx)
        try:
            # Admin role can run execute_python
            auth_res_py = authorize_sensitive_tool("execute_python", {"code": "print(1)"})
            self.assertTrue(auth_res_py.allowed)

            # Admin role can run control_device
            auth_res_dev = authorize_sensitive_tool("control_device", {"device": "fan", "action": "on"})
            self.assertTrue(auth_res_dev.allowed)
        finally:
            active_user_var.reset(token)


if __name__ == "__main__":
    unittest.main()
