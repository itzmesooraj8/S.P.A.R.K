"""
SPARK Identity Engine — Email Intelligence
==========================================
Aggregates email intelligence from multiple public sources:
  - Hunter.io  → find email addresses, company domain info
  - HIBP (Have I Been Pwned) → check breach exposure

API keys must be stored in the Combat Vault:
  vault.set_secret("hunter_api_key", "...", passphrase)
  vault.set_secret("hibp_api_key", "...", passphrase)
"""
import logging
from typing import Optional

log = logging.getLogger(__name__)

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False

_HUNTER_BASE = "https://api.hunter.io/v2"
_HIBP_BASE   = "https://haveibeenpwned.com/api/v3"
_TIMEOUT     = 15


async def _get_vault_key(key: str) -> Optional[str]:
    """Attempt to retrieve a key from the combat vault without a passphrase (env fallback)."""
    import os
    env_map = {
        "hunter_api_key": "HUNTER_API_KEY",
        "hibp_api_key":   "HIBP_API_KEY",
    }
    return os.environ.get(env_map.get(key, ""), None)


async def _hunter_email_verify(email: str, api_key: str) -> dict:
    if not _HTTPX:
        return {"available": False, "reason": "httpx not installed"}
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_HUNTER_BASE}/email-verifier",
            params={"email": email, "api_key": api_key},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            return r.json().get("data", {})
        return {"error": f"HTTP {r.status_code}"}


async def _hibp_check(email: str, api_key: str) -> list[dict]:
    if not _HTTPX:
        return []
    async with httpx.AsyncClient() as client:
        r = await client.get(
            f"{_HIBP_BASE}/breachedaccount/{email}",
            headers={
                "hibp-api-key":  api_key,
                "user-agent":    "SPARK-OSINT-Platform/1.0",
            },
            params={"truncateResponse": "false"},
            timeout=_TIMEOUT,
        )
        if r.status_code == 200:
            breaches = r.json()
            return [
                {
                    "name":             b.get("Name"),
                    "breach_date":      b.get("BreachDate"),
                    "added_date":       b.get("AddedDate"),
                    "pwn_count":        b.get("PwnCount"),
                    "description":      b.get("Description", "")[:300],
                    "data_classes":     b.get("DataClasses", []),
                    "is_verified":      b.get("IsVerified"),
                    "is_sensitive":     b.get("IsSensitive"),
                }
                for b in breaches
            ]
        if r.status_code == 404:
            return []
        return [{"error": f"HTTP {r.status_code}"}]


async def run_email_intel(email: str) -> dict:
    hunter_key = await _get_vault_key("hunter_api_key")
    hibp_key   = await _get_vault_key("hibp_api_key")

    results: dict = {"email": email, "sources": {}}

    if hunter_key:
        try:
            results["sources"]["hunter"] = await _hunter_email_verify(email, hunter_key)
        except Exception as e:
            results["sources"]["hunter"] = {"error": str(e)}
    else:
        results["sources"]["hunter"] = {
            "available": False,
            "reason":    "No HUNTER_API_KEY in environment or vault.",
        }

    if hibp_key:
        try:
            breaches = await _hibp_check(email, hibp_key)
            results["sources"]["hibp"] = {
                "breach_count": len(breaches),
                "breaches":     breaches,
            }
        except Exception as e:
            results["sources"]["hibp"] = {"error": str(e)}
    else:
        results["sources"]["hibp"] = {
            "available": False,
            "reason":    "No HIBP_API_KEY in environment or vault.",
        }

    return results
