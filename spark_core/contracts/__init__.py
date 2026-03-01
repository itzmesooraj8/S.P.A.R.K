"""
SPARK API Contract Models — Single Source of Truth.

These Pydantic models define the exact shape of every message crossing the
frontend ↔ backend boundary.  The TypeScript mirror lives at:
  src/types/contracts.ts

Versioning: bump API_SCHEMA_VERSION whenever a breaking field change is made.
"""

API_SCHEMA_VERSION = 1
