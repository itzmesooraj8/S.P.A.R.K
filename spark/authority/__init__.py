"""
Spark Authority — Permission & Safety Layer

Every action must pass authority validation.
- Can Read Screen?
- Can Open Browser?
- Can Execute Shell?
- Can Send Email?
- Can Spend Money?
"""

from spark.authority.validator import ActionValidator, Permission
from spark.authority.policy import AuthorityPolicy

__all__ = ["ActionValidator", "Permission", "AuthorityPolicy"]
