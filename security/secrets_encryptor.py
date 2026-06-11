"""Secure Secrets Encryption Helper using Cryptography Fernet."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from cryptography.fernet import Fernet

logger = logging.getLogger("SPARK_SECRETS_ENCRYPTOR")

DEFAULT_KEY_PATH = "knowledge_base/secret.key"


class SecretsEncryptor:
    """Provides secure encryption and decryption of sensitive string values (e.g. keys, tokens)."""

    def __init__(self, key_path: str | None = None):
        self.key_path = key_path or os.getenv("SPARK_ENCRYPTION_KEY_PATH", DEFAULT_KEY_PATH)
        self._key = self._load_or_generate_key()
        self._cipher = Fernet(self._key)

    def _load_or_generate_key(self) -> bytes:
        """Loads key from environment or file, or generates a new one if missing."""
        # 1. Check environment variable
        env_key = os.getenv("SPARK_ENCRYPTION_KEY")
        if env_key:
            try:
                # Ensure it is valid base64 urlsafe key
                return env_key.encode("utf-8")
            except Exception:
                logger.error("SPARK_ENCRYPTION_KEY env var is not valid base64 bytes.")

        # 2. Check file
        key_file = Path(self.key_path)
        if key_file.exists():
            try:
                return key_file.read_bytes()
            except Exception as exc:
                logger.error("Failed to read encryption key file: %s", exc)

        # 3. Generate new key
        logger.info("Generating new secure secrets encryption key at %s", self.key_path)
        new_key = Fernet.generate_key()
        try:
            key_file.parent.mkdir(parents=True, exist_ok=True)
            key_file.write_bytes(new_key)
            # Make file read-only on unix if needed (not applicable for basic windows workspace)
        except Exception as exc:
            logger.error("Failed to save generated encryption key: %s", exc)
        return new_key

    def encrypt(self, plain_text: str) -> str:
        """Encrypts a plain text string. Returns base64 token string."""
        if not plain_text:
            return ""
        try:
            cipher_bytes = self._cipher.encrypt(plain_text.encode("utf-8"))
            return cipher_bytes.decode("utf-8")
        except Exception as exc:
            logger.error("Failed to encrypt value: %s", exc)
            raise ValueError("Encryption failed") from exc

    def decrypt(self, cipher_text: str) -> str:
        """Decrypts an encrypted string back to plain text."""
        if not cipher_text:
            return ""
        try:
            plain_bytes = self._cipher.decrypt(cipher_text.encode("utf-8"))
            return plain_bytes.decode("utf-8")
        except Exception as exc:
            logger.error("Failed to decrypt value: %s", exc)
            raise ValueError("Decryption failed") from exc


# Global encryptor instance
secrets_encryptor = SecretsEncryptor()
