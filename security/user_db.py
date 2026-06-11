"""Secure Multi-User SQLite Database Management for S.P.A.R.K."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import secrets
import sqlite3
import time
from typing import Any

logger = logging.getLogger("SPARK_USER_DB")

DEFAULT_DB_PATH = "knowledge_base/users.db"


def hash_password(password: str, salt: bytes | None = None) -> tuple[str, str]:
    """Hash a password using PBKDF2-SHA256 with 100,000 iterations."""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return base64.b64encode(dk).decode("utf-8"), base64.b64encode(salt).decode("utf-8")


def verify_password(password: str, password_hash: str, salt_b64: str) -> bool:
    """Verify a candidate password against the stored hash and salt."""
    try:
        salt = base64.b64decode(salt_b64.encode("utf-8"))
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        candidate_hash = base64.b64encode(dk).decode("utf-8")
        return secrets.compare_digest(password_hash, candidate_hash)
    except Exception as exc:
        logger.error("Error during password verification: %s", exc)
        return False


class UserDatabaseManager:
    """Manages S.P.A.R.K. users, password verification, roles, permissions, and token revocation."""

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path or os.getenv("SPARK_USER_DB_PATH", DEFAULT_DB_PATH)
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initializes database schema if tables do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 1. Users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    salt TEXT NOT NULL,
                    role TEXT NOT NULL,
                    permissions TEXT NOT NULL, -- JSON array
                    mfa_secret TEXT,
                    mfa_enabled INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # 2. Token blacklist table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blacklisted_tokens (
                    jti TEXT PRIMARY KEY,
                    expires_at INTEGER NOT NULL
                )
            """)
            conn.commit()

    def create_user(
        self, username: str, password: str, role: str = "viewer", permissions: list[str] | None = None
    ) -> bool:
        """Creates a new user record. Returns True on success, False if user already exists."""
        username = username.strip().lower()
        if not username or not password:
            return False
        if permissions is None:
            permissions = ["status"]

        password_hash, salt = hash_password(password)
        permissions_json = json.dumps(permissions)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO users (username, password_hash, salt, role, permissions) VALUES (?, ?, ?, ?, ?)",
                    (username, password_hash, salt, role, permissions_json),
                )
                conn.commit()
            logger.info("Successfully created user: %s (role: %s)", username, role)
            return True
        except sqlite3.IntegrityError:
            logger.warning("Attempted to create duplicate user: %s", username)
            return False
        except Exception as exc:
            logger.error("Failed to create user %s: %s", username, exc)
            return False

    def get_user(self, username: str) -> dict[str, Any] | None:
        """Retrieves a user by username."""
        username = username.strip().lower()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
                row = cursor.fetchone()
                if row:
                    data = dict(row)
                    # Parse permissions JSON
                    try:
                        data["permissions"] = json.loads(data["permissions"])
                    except Exception:
                        data["permissions"] = []
                    return data
            return None
        except Exception as exc:
            logger.error("Error retrieving user %s: %s", username, exc)
            return None

    def list_users(self) -> list[dict[str, Any]]:
        """Lists all registered users."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, username, role, permissions, mfa_enabled, created_at FROM users")
                rows = cursor.fetchall()
                users = []
                for row in rows:
                    data = dict(row)
                    try:
                        data["permissions"] = json.loads(data["permissions"])
                    except Exception:
                        data["permissions"] = []
                    users.append(data)
                return users
        except Exception as exc:
            logger.error("Error listing users: %s", exc)
            return []

    def update_user_role_and_permissions(self, username: str, role: str, permissions: list[str]) -> bool:
        """Updates user role and permissions in the database."""
        username = username.strip().lower()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET role = ?, permissions = ? WHERE username = ?",
                    (role, json.dumps(permissions), username),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as exc:
            logger.error("Error updating role/permissions for %s: %s", username, exc)
            return False

    def update_user_password(self, username: str, new_password: str) -> bool:
        """Updates user password in the database."""
        username = username.strip().lower()
        password_hash, salt = hash_password(new_password)
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET password_hash = ?, salt = ? WHERE username = ?",
                    (password_hash, salt, username),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as exc:
            logger.error("Error updating password for %s: %s", username, exc)
            return False

    def delete_user(self, username: str) -> bool:
        """Deletes a user from the database."""
        username = username.strip().lower()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM users WHERE username = ?", (username,))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as exc:
            logger.error("Error deleting user %s: %s", username, exc)
            return False

    def authenticate_user(self, username: str, password: str | None) -> dict[str, Any] | None:
        """Authenticates a user. Returns the user dict if successful, else None."""
        if not password:
            return None
        user = self.get_user(username)
        if not user:
            return None

        if verify_password(password, user["password_hash"], user["salt"]):
            return user
        return None

    def enable_mfa(self, username: str, secret: str) -> bool:
        """Stores the MFA secret and marks MFA as enabled."""
        username = username.strip().lower()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET mfa_secret = ?, mfa_enabled = 1 WHERE username = ?",
                    (secret, username),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as exc:
            logger.error("Failed to enable MFA for %s: %s", username, exc)
            return False

    def disable_mfa(self, username: str) -> bool:
        """Removes the MFA secret and disables MFA."""
        username = username.strip().lower()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE users SET mfa_secret = NULL, mfa_enabled = 0 WHERE username = ?",
                    (username,),
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as exc:
            logger.error("Failed to disable MFA for %s: %s", username, exc)
            return False

    def blacklist_token(self, jti: str, expires_at: int) -> bool:
        """Blacklists a token JTI until it expires."""
        if not jti:
            return False
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO blacklisted_tokens (jti, expires_at) VALUES (?, ?)",
                    (jti, expires_at),
                )
                conn.commit()
            return True
        except Exception as exc:
            logger.error("Failed to blacklist token JTI %s: %s", jti, exc)
            return False

    def is_token_blacklisted(self, jti: str) -> bool:
        """Checks if a token JTI is blacklisted."""
        if not jti:
            return True
        # Proactively prune expired blacklisted tokens
        self._prune_blacklist()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1 FROM blacklisted_tokens WHERE jti = ?", (jti,))
                return cursor.fetchone() is not None
        except Exception as exc:
            logger.error("Failed to check blacklist for JTI %s: %s", jti, exc)
            return True

    def _prune_blacklist(self) -> None:
        """Deletes expired tokens from the blacklist to keep the table compact."""
        now = int(time.time())
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM blacklisted_tokens WHERE expires_at <= ?", (now,))
                conn.commit()
        except Exception as exc:
            logger.error("Failed to prune blacklisted tokens: %s", exc)

    def close(self) -> None:
        """Closes the manager (noop as connections are transient)."""
        pass


# Global user DB manager instance
user_db_manager = UserDatabaseManager()
