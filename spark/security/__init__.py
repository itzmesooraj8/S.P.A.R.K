"""
Spark Security — Secrets Management, Permission Scopes, Sandboxed Execution

Before production:
- Secrets Management (API keys, tokens, passwords never in code)
- Permission Scopes (independently controlled)
- Sandboxed Execution (tools run in restricted contexts)
"""

from spark.security.secrets import SecretsManager
from spark.security.scopes import PermissionScope
from spark.security.sandbox import Sandbox

__all__ = ["SecretsManager", "PermissionScope", "Sandbox"]
