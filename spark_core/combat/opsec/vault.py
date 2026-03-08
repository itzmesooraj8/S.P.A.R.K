"""
SPARK Combat Vault — AES-256-GCM Encrypted Secret Store
=========================================================
Stores API keys and sensitive strings in an encrypted file.
The encryption key is derived from the combat passphrase using PBKDF2-HMAC-SHA256.
The vault file itself is safe to commit — it cannot be decrypted without the passphrase.

  vault.set_secret("shodan_key", "abc123", passphrase)
  vault.get_secret("shodan_key", passphrase)       → "abc123"
  vault.list_keys(passphrase)                       → ["shodan_key"]
"""
import os
import json
import hashlib
import secrets as _secrets
from pathlib import Path
from typing import Optional

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

_VAULT_FILE = Path(__file__).parent.parent.parent.parent / "config" / "secrets.vault"
_SALT_FILE  = _VAULT_FILE.with_suffix(".salt")

_KDF_ITERATIONS = 260_000
_KEY_LEN        = 32   # 256-bit
_NONCE_LEN      = 12   # 96-bit GCM nonce


class VaultDecryptionError(Exception):
    """Raised when the vault cannot be decrypted (wrong passphrase)."""
    pass


class CombatVault:
    """AES-256-GCM encrypted JSON key-value store."""

    # ── Key derivation ─────────────────────────────────────────────────────

    def _get_or_create_salt(self) -> bytes:
        _VAULT_FILE.parent.mkdir(parents=True, exist_ok=True)
        if _SALT_FILE.exists():
            return bytes.fromhex(_SALT_FILE.read_text().strip())
        salt = _secrets.token_bytes(32)
        _SALT_FILE.write_text(salt.hex())
        return salt

    def _derive_key(self, passphrase: str) -> bytes:
        salt = self._get_or_create_salt()
        return hashlib.pbkdf2_hmac(
            "sha256",
            passphrase.encode("utf-8"),
            salt,
            iterations=_KDF_ITERATIONS,
            dklen=_KEY_LEN,
        )

    # ── Encryption helpers ─────────────────────────────────────────────────

    def _encrypt(self, plaintext: bytes, key: bytes) -> bytes:
        nonce = _secrets.token_bytes(_NONCE_LEN)
        ct    = AESGCM(key).encrypt(nonce, plaintext, None)
        return nonce + ct

    def _decrypt(self, blob: bytes, key: bytes) -> bytes:
        nonce, ct = blob[:_NONCE_LEN], blob[_NONCE_LEN:]
        try:
            return AESGCM(key).decrypt(nonce, ct, None)
        except Exception:
            raise VaultDecryptionError("Vault decryption failed. Wrong passphrase?")

    # ── Vault I/O ──────────────────────────────────────────────────────────

    def _read_all(self, passphrase: str) -> dict[str, str]:
        if not _VAULT_FILE.exists():
            return {}
        blob  = bytes.fromhex(_VAULT_FILE.read_text().strip())
        key   = self._derive_key(passphrase)
        plain = self._decrypt(blob, key)
        return json.loads(plain.decode("utf-8"))

    def _write_all(self, data: dict[str, str], passphrase: str) -> None:
        key       = self._derive_key(passphrase)
        plain     = json.dumps(data).encode("utf-8")
        encrypted = self._encrypt(plain, key)
        _VAULT_FILE.write_text(encrypted.hex())

    # ── Public API ─────────────────────────────────────────────────────────

    def set_secret(self, key: str, value: str, passphrase: str) -> None:
        data = self._read_all(passphrase)
        data[key] = value
        self._write_all(data, passphrase)

    def get_secret(self, key: str, passphrase: str) -> Optional[str]:
        data = self._read_all(passphrase)
        return data.get(key)

    def delete_secret(self, key: str, passphrase: str) -> bool:
        data = self._read_all(passphrase)
        if key not in data:
            return False
        del data[key]
        self._write_all(data, passphrase)
        return True

    def list_keys(self, passphrase: str) -> list[str]:
        data = self._read_all(passphrase)
        return sorted(data.keys())

    def is_empty(self) -> bool:
        return not _VAULT_FILE.exists()


combat_vault = CombatVault()
