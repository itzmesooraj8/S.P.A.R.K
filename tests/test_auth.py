import os
import unittest
from unittest.mock import patch

from api.auth import (
    AuthLoginRequest,
    AuthenticatedUser,
    credentials_are_valid,
    get_static_operator_token,
    issue_token_pair,
    token_has_permission,
    validate_access_token_or_static,
    validate_signed_token,
)


class AuthTests(unittest.TestCase):
    def setUp(self) -> None:
        from security.user_db import user_db_manager
        self.original_db_path = user_db_manager.db_path
        self.test_db_path = "knowledge_base/test_auth_legacy.db"
        user_db_manager.db_path = self.test_db_path
        user_db_manager._init_db()
        self.db = user_db_manager
        # Clear tables for absolute test isolation
        with self.db._get_connection() as conn:
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM blacklisted_tokens")
            conn.commit()

    def tearDown(self) -> None:
        from security.user_db import user_db_manager
        self.db.close()
        user_db_manager.db_path = self.original_db_path
        user_db_manager._init_db()


    def test_password_login_issues_signed_tokens_without_exposing_static_secret(self) -> None:
        env = {
            "SPARK_ACCESS_TOKEN": "unit-static-token",
            "SPARK_AUTH_SECRET": "unit-signing-secret",
            "SPARK_OPERATOR_PASSWORD": "correct-horse-battery-staple",
            "SPARK_OPERATOR_USERNAME": "operator",
        }
        with patch.dict(os.environ, env, clear=False):
            login = AuthLoginRequest(username="operator", password="correct-horse-battery-staple")
            self.assertTrue(credentials_are_valid(login))

            tokens = issue_token_pair()

            self.assertNotEqual(tokens.access_token, get_static_operator_token())
            self.assertNotEqual(tokens.refresh_token, get_static_operator_token())
            self.assertTrue(validate_signed_token(tokens.access_token, expected_type="access"))
            self.assertTrue(validate_signed_token(tokens.refresh_token, expected_type="refresh"))

    def test_invalid_password_is_rejected(self) -> None:
        env = {
            "SPARK_ACCESS_TOKEN": "unit-static-token",
            "SPARK_AUTH_SECRET": "unit-signing-secret",
            "SPARK_OPERATOR_PASSWORD": "correct-password",
            "SPARK_OPERATOR_USERNAME": "operator",
        }
        with patch.dict(os.environ, env, clear=False):
            login = AuthLoginRequest(username="operator", password="wrong-password")
            self.assertFalse(credentials_are_valid(login))

    def test_existing_static_token_still_authorizes_legacy_local_clients(self) -> None:
        with patch.dict(os.environ, {"SPARK_ACCESS_TOKEN": "unit-static-token"}, clear=False):
            self.assertTrue(validate_access_token_or_static("unit-static-token"))
            self.assertFalse(validate_access_token_or_static("not-the-token"))

    def test_signed_token_permissions_are_enforced(self) -> None:
        env = {"SPARK_ACCESS_TOKEN": "unit-static-token", "SPARK_AUTH_SECRET": "unit-signing-secret"}
        with patch.dict(os.environ, env, clear=False):
            user = AuthenticatedUser(username="viewer", role="viewer", permissions=["status"])
            tokens = issue_token_pair(user=user)

            self.assertTrue(token_has_permission(tokens.access_token, "status"))
            self.assertFalse(token_has_permission(tokens.access_token, "admin"))
            self.assertFalse(token_has_permission("not-a-token", "status"))

    def test_admin_permission_allows_any_scope(self) -> None:
        env = {"SPARK_ACCESS_TOKEN": "unit-static-token", "SPARK_AUTH_SECRET": "unit-signing-secret"}
        with patch.dict(os.environ, env, clear=False):
            user = AuthenticatedUser(username="operator", role="operator", permissions=["admin"])
            tokens = issue_token_pair(user=user)

            self.assertTrue(token_has_permission(tokens.access_token, "security:audit"))
            self.assertTrue(token_has_permission("unit-static-token", "security:audit"))


if __name__ == "__main__":
    unittest.main()
