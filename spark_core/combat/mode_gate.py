"""
SPARK Combat Mode Gate
======================
Manages passphrase-protected combat mode activation.
Generates short-lived session tokens that gate all /api/combat/* endpoints.
Passphrase is hashed with PBKDF2-HMAC-SHA256 — never stored in plaintext.
"""
import os
import time
import hmac
import hashlib
import secrets
import threading
from pathlib import Path
from typing import Optional
from fastapi import HTTPException, Header, Request

# ── Paths ─────────────────────────────────────────────────────────────────────
_BASE_DIR  = Path(__file__).parent.parent.parent
_HASH_FILE = _BASE_DIR / "spark_memory_db" / "combat_passphrase.hash"

# ── In-memory token store (session-scoped, not persisted) ─────────────────────
_active_tokens: dict[str, float] = {}          # token → expiry (unix)
_lock          = threading.Lock()
TOKEN_TTL      = 3600 * 8                       # 8-hour sessions


# ── Passphrase management ─────────────────────────────────────────────────────

def _pbkdf2(passphrase: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        "sha256",
        passphrase.encode("utf-8"),
        salt,
        iterations=260_000,
        dklen=32,
    )


def passphrase_is_set() -> bool:
    return _HASH_FILE.exists()


def set_passphrase(passphrase: str) -> None:
    """Store a new passphrase hash. Call from settings / first-run setup."""
    if not passphrase or len(passphrase) < 8:
        raise ValueError("Combat passphrase must be at least 8 characters.")
    salt  = secrets.token_bytes(32)
    dk    = _pbkdf2(passphrase, salt)
    blob  = (salt + dk).hex()
    _HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HASH_FILE.write_text(blob)


def verify_passphrase(passphrase: str) -> bool:
    """Return True if passphrase matches the stored hash."""
    if not _HASH_FILE.exists():
        return False
    blob = bytes.fromhex(_HASH_FILE.read_text().strip())
    salt, stored_dk = blob[:32], blob[32:]
    candidate_dk    = _pbkdf2(passphrase, salt)
    return hmac.compare_digest(stored_dk, candidate_dk)


def reset_passphrase() -> None:
    """Delete the stored passphrase hash, allowing a new one to be set."""
    revoke_all()
    if _HASH_FILE.exists():
        _HASH_FILE.unlink()


# ── Token management ──────────────────────────────────────────────────────────

def issue_token() -> str:
    token  = secrets.token_urlsafe(32)
    expiry = time.time() + TOKEN_TTL
    with _lock:
        _prune()
        _active_tokens[token] = expiry
    return token


def revoke_all() -> None:
    with _lock:
        _active_tokens.clear()


def is_token_valid(token: str) -> bool:
    with _lock:
        expiry = _active_tokens.get(token)
        if expiry is None:
            return False
        if time.time() > expiry:
            del _active_tokens[token]
            return False
        return True


def _prune() -> None:
    """Remove expired tokens (called under lock)."""
    now    = time.time()
    stale  = [t for t, exp in _active_tokens.items() if now > exp]
    for t in stale:
        del _active_tokens[t]


# ── FastAPI dependency ────────────────────────────────────────────────────────

async def require_combat_mode(
    x_combat_token: Optional[str] = Header(None, alias="X-Combat-Token"),
) -> str:
    """FastAPI dependency: gates any /api/combat/* endpoint."""
    if not x_combat_token or not is_token_valid(x_combat_token):
        raise HTTPException(
            status_code=403,
            detail={
                "error":   "COMBAT_MODE_LOCKED",
                "message": "Combat mode is not active. Authenticate at /api/combat/auth/activate first.",
            },
        )
    return x_combat_token


# ── Singleton export ──────────────────────────────────────────────────────────
combat_gate = {
    "passphrase_is_set": passphrase_is_set,
    "set_passphrase":    set_passphrase,
    "verify_passphrase": verify_passphrase,
    "issue_token":       issue_token,
    "revoke_all":        revoke_all,
    "is_token_valid":    is_token_valid,
    "require":           require_combat_mode,
}
