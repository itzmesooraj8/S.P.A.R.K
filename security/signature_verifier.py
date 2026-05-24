from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import logging
from typing import Any

logger = logging.getLogger(__name__)

def get_secret_key() -> bytes:
    """Retrieve secret key from environment or fall back to SPARK_TOKEN."""
    key = os.getenv("SPARK_SECRET_KEY") or os.getenv("SPARK_TOKEN") or "change-this-token"
    return key.encode("utf-8")

def canonical_serialize(payload: dict[str, Any]) -> bytes:
    """Convert dict to a canonical JSON string bytes representation."""
    serialized = json.dumps(payload, sort_keys=True, separators=(',', ':'))
    return serialized.encode("utf-8")

def generate_signature(payload: dict[str, Any], secret_key: bytes) -> str:
    """Generate HMAC-SHA256 signature for canonical payload bytes."""
    payload_bytes = canonical_serialize(payload)
    return hmac.new(secret_key, payload_bytes, hashlib.sha256).hexdigest()

def verify_signature(payload: dict[str, Any], signature: str, secret_key: bytes) -> bool:
    """Verify hmac signature matches canonical payload."""
    expected = generate_signature(payload, secret_key)
    return hmac.compare_digest(expected, signature)

def verify_remote_request(payload: dict[str, Any], signature: str, max_drift_seconds: int = 300) -> bool:
    """
    Validate that:
    1. Signature is correct.
    2. Timestamp exists and is within current time + drift window to prevent replay attacks.
    """
    timestamp = payload.get("timestamp")
    if timestamp is None:
        logger.warning("Remote request rejected: missing timestamp")
        return False

    try:
        ts = float(timestamp)
    except (ValueError, TypeError):
        logger.warning(f"Remote request rejected: invalid timestamp format '{timestamp}'")
        return False

    now = time.time()
    if abs(now - ts) > max_drift_seconds:
        logger.warning(f"Remote request rejected: timestamp drift too large (drift={abs(now - ts)}s, limit={max_drift_seconds}s)")
        return False

    secret_key = get_secret_key()
    if not verify_signature(payload, signature, secret_key):
        logger.warning("Remote request rejected: signature mismatch")
        return False

    return True
