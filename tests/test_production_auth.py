"""Unit and Integration Tests for S.P.A.R.K. Production Grade Security Upgrades.

Tests password hashing, user DB administration, token rotation, TOTP MFA checks,
IP whitelisting middleware, and secrets encryption.
"""

from __future__ import annotations

import os
import time
import unittest
from unittest.mock import patch

import pyotp
from fastapi.testclient import TestClient

from api.auth import (
    AuthLoginRequest,
    AuthRefreshRequest,
    AuthenticatedUser,
    credentials_are_valid,
    issue_token_pair,
    validate_access_token,
    validate_signed_token,
)
from api.server import app
from security.secrets_encryptor import SecretsEncryptor
from security.user_db import UserDatabaseManager, hash_password, verify_password


class ProductionSecurityTests(unittest.TestCase):

    def setUp(self):
        # Use a temporary SQLite database for testing, pointing global user_db_manager to it
        from security.user_db import user_db_manager
        self.original_db_path = user_db_manager.db_path
        self.test_db_path = "knowledge_base/test_users.db"
        user_db_manager.db_path = self.test_db_path
        user_db_manager._init_db()
        self.db = user_db_manager
        # Clear tables for test isolation
        with self.db._get_connection() as conn:
            conn.execute("DELETE FROM users")
            conn.execute("DELETE FROM blacklisted_tokens")
            conn.commit()
        self.client = TestClient(app)

    def tearDown(self):
        from security.user_db import user_db_manager
        self.db.close()
        user_db_manager.db_path = self.original_db_path
        user_db_manager._init_db()


    # --- 1. Password Hashing and Database Verification ---
    def test_password_hashing_and_verification(self):
        pw = "super-secret-password-123"
        pwd_hash, salt = hash_password(pw)

        self.assertIsNotNone(pwd_hash)
        self.assertIsNotNone(salt)
        self.assertNotEqual(pw, pwd_hash)

        # Verify correct credentials
        self.assertTrue(verify_password(pw, pwd_hash, salt))
        # Verify incorrect credentials
        self.assertFalse(verify_password("wrong-password", pwd_hash, salt))

    def test_user_creation_and_retrieval(self):
        username = "agent_smith"
        password = "smith-password"
        permissions = ["chat", "tools"]

        # Creation
        success = self.db.create_user(username, password, role="operator", permissions=permissions)
        self.assertTrue(success)

        # Re-creation fails
        duplicate = self.db.create_user(username, "another-password")
        self.assertFalse(duplicate)

        # Retrieval
        user = self.db.get_user(username)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], username)
        self.assertEqual(user["role"], "operator")
        self.assertEqual(user["permissions"], permissions)
        self.assertEqual(user["mfa_enabled"], 0)

        # Authentication success
        authenticated = self.db.authenticate_user(username, password)
        self.assertIsNotNone(authenticated)

        # Authentication failure
        auth_fail = self.db.authenticate_user(username, "wrong-password")
        self.assertIsNone(auth_fail)

    # --- 2. Token Rotation and Blacklisting ---
    def test_token_issuance_rotation_and_revocation(self):
        user = AuthenticatedUser(username="operator_test", role="operator", permissions=["chat", "status"])
        tokens = issue_token_pair(user)

        # Token signatures are valid
        payload_access = validate_access_token(tokens.access_token)
        payload_refresh = validate_signed_token(tokens.refresh_token, expected_type="refresh")

        self.assertIsNotNone(payload_access)
        self.assertIsNotNone(payload_refresh)
        self.assertEqual(payload_access.subject, "operator_test")
        self.assertEqual(payload_refresh.subject, "operator_test")

        # Invalidate/blacklist access token
        self.db.blacklist_token(payload_access.jwt_id, payload_access.expires_at)
        self.assertTrue(self.db.is_token_blacklisted(payload_access.jwt_id))

        # Access token validation fails now
        self.assertIsNone(validate_access_token(tokens.access_token))

    # --- 3. Multi-Factor Authentication (MFA/TOTP) ---
    def test_mfa_setup_and_verification(self):
        username = "mfa_user"
        self.db.create_user(username, "password123")

        # Generate TOTP Secret
        secret = pyotp.random_base32()
        totp = pyotp.TOTP(secret)

        # Verify initial state: MFA not enabled
        user = self.db.get_user(username)
        self.assertEqual(user["mfa_enabled"], 0)

        # Enable MFA
        self.db.enable_mfa(username, secret)
        user = self.db.get_user(username)
        self.assertEqual(user["mfa_enabled"], 1)
        self.assertEqual(user["mfa_secret"], secret)

        # Verify OTP code
        valid_code = totp.now()
        self.assertTrue(totp.verify(valid_code))
        self.assertFalse(totp.verify("000000"))

    # --- 4. Secrets Encryption (Fernet) ---
    def test_secrets_encryption_fernet(self):
        temp_key_path = "knowledge_base/test_secret.key"
        if os.path.exists(temp_key_path):
            os.remove(temp_key_path)

        encryptor = SecretsEncryptor(key_path=temp_key_path)
        secret_data = "my-nasa-firms-api-key-string"

        encrypted = encryptor.encrypt(secret_data)
        self.assertNotEqual(secret_data, encrypted)

        decrypted = encryptor.decrypt(encrypted)
        self.assertEqual(secret_data, decrypted)

        # Cleanup key file
        if os.path.exists(temp_key_path):
            os.remove(temp_key_path)

    # --- 5. IP Restriction Middleware ---
    def test_ip_restriction_middleware_blocking(self):
        # Patch the allowed IP env var
        with patch.dict(os.environ, {"SPARK_ALLOWED_IPS": "192.168.1.50"}):
            # 1. Access from local loopback (allowed)
            response_local = self.client.get("/ping")
            self.assertEqual(response_local.status_code, 200)

            # 2. Access from a non-whitelisted remote IP
            # We construct a mock client request with a remote IP
            response_blocked = self.client.get("/ping", headers={"x-forwarded-for": "10.0.0.99"})
            # Note: TestClient request.client.host is usually 'testclient', which doesn't trigger loopback checks.
            # To test the IP restriction middleware thoroughly, we pass remote client headers if handled, or mock client host:
            client_ip = "10.0.0.99"
            with patch("fastapi.Request.client", new=unittest.mock.PropertyMock(return_value=unittest.mock.MagicMock(host=client_ip))):
                response_blocked = self.client.get("/ping")
                self.assertEqual(response_blocked.status_code, 403)
                self.assertIn("IP address access restricted", response_blocked.json()["error"])

            # 3. Access from a whitelisted remote IP
            client_ip = "192.168.1.50"
            with patch("fastapi.Request.client", new=unittest.mock.PropertyMock(return_value=unittest.mock.MagicMock(host=client_ip))):
                response_allowed = self.client.get("/ping")
                self.assertEqual(response_allowed.status_code, 200)


if __name__ == "__main__":
    unittest.main()
