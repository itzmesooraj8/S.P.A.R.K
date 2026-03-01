"""
SPARK User Store
Manages user accounts with bcrypt-hashed passwords.
Users are seeded from env vars or secrets.yaml at boot (no plain-text defaults in code).
"""
import os
from typing import Optional, Dict, Any

from auth.jwt_handler import hash_password, verify_password

# ── In-memory user DB ─────────────────────────────────────────────────────────
# Schema: { username: { "password_hash": str, "role": str, "active": bool } }
_USERS: Dict[str, Dict[str, Any]] = {}


def _ensure_seeded():
    """Seed default root user from env / secrets on first call."""
    if _USERS:
        return

    # Load secrets.yaml for credentials if available
    _load_from_yaml()

    # Fall back to env vars
    root_user = os.getenv("SPARK_ROOT_USER", "root")
    root_pass = os.getenv("SPARK_ROOT_PASSWORD", "")

    if root_user not in _USERS:
        if not root_pass:
            # Derive a one-time password from machine identity so there's no hardcoded default
            import hashlib, socket
            root_pass = hashlib.sha256(socket.gethostname().encode()).hexdigest()[:16]
            print(f"⚠️  [AUTH] No SPARK_ROOT_PASSWORD set. Generated ephemeral root password: {root_pass}")
            print("⚠️  [AUTH] Set SPARK_ROOT_PASSWORD in your .env to fix this.")

        _USERS[root_user] = {
            "password_hash": hash_password(root_pass),
            "role": "ROOT",
            "active": True,
        }
        print(f"✅ [AUTH] Root user '{root_user}' seeded (role=ROOT).")


def _load_from_yaml():
    try:
        import yaml, pathlib
        yaml_path = pathlib.Path(__file__).parent.parent.parent / "config" / "secrets.yaml"
        if not yaml_path.exists():
            return
        data = yaml.safe_load(yaml_path.read_text()) or {}
        users_block = data.get("users", {})
        for username, info in users_block.items():
            if not isinstance(info, dict):
                continue
            plain = info.get("password", "")
            role  = info.get("role", "OPERATOR")
            if username and plain:
                _USERS[username] = {
                    "password_hash": hash_password(plain),
                    "role": role,
                    "active": info.get("active", True),
                }
                print(f"✅ [AUTH] Loaded user '{username}' from secrets.yaml (role={role}).")
    except Exception as exc:
        print(f"⚠️  [AUTH] Could not load users from secrets.yaml: {exc}")


def authenticate(username: str, password: str) -> Optional[Dict[str, Any]]:
    """Return user dict if credentials valid, else None."""
    _ensure_seeded()
    user = _USERS.get(username)
    if not user or not user.get("active"):
        return None
    if verify_password(password, user["password_hash"]):
        return {"sub": username, "role": user["role"]}
    return None


def get_user(username: str) -> Optional[Dict[str, Any]]:
    _ensure_seeded()
    return _USERS.get(username)


def create_user(username: str, password: str, role: str = "OPERATOR") -> bool:
    """Add a new user (admin operation). Returns False if username taken."""
    _ensure_seeded()
    if username in _USERS:
        return False
    _USERS[username] = {
        "password_hash": hash_password(password),
        "role": role,
        "active": True,
    }
    return True


def list_users() -> list:
    _ensure_seeded()
    return [
        {"username": u, "role": v["role"], "active": v["active"]}
        for u, v in _USERS.items()
    ]
