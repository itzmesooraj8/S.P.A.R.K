"""
SPARK OpSec — Scope Enforcer
=============================
All active-recon operations MUST declare a target scope list first.
Any attempt to reach a target outside the declared scope raises OutOfScopeError.

This is an explicit safety control:  operators must affirmatively add targets
to scope before any packets are sent.
"""
import re
import ipaddress
import threading
from pathlib import Path
import json

_SCOPE_FILE = Path(__file__).parent.parent.parent.parent / "spark_memory_db" / "combat_scope.json"


class OutOfScopeError(Exception):
    """Raised when an operation targets a host outside the declared scope."""
    pass


class ScopeEnforcer:
    """Thread-safe singleton that maintains the engagement target list."""

    def __init__(self) -> None:
        self._targets: set[str] = set()
        self._lock = threading.Lock()
        self._load()

    # ── Persistence ────────────────────────────────────────────────────────

    def _load(self) -> None:
        if _SCOPE_FILE.exists():
            try:
                data = json.loads(_SCOPE_FILE.read_text())
                self._targets = set(data.get("targets", []))
            except Exception:
                self._targets = set()

    def _save(self) -> None:
        _SCOPE_FILE.parent.mkdir(parents=True, exist_ok=True)
        _SCOPE_FILE.write_text(json.dumps({"targets": sorted(self._targets)}, indent=2))

    # ── Mutations ──────────────────────────────────────────────────────────

    def add_target(self, target: str) -> None:
        normalised = self._normalise(target)
        with self._lock:
            self._targets.add(normalised)
            self._save()

    def remove_target(self, target: str) -> None:
        normalised = self._normalise(target)
        with self._lock:
            self._targets.discard(normalised)
            self._save()

    def clear(self) -> None:
        with self._lock:
            self._targets.clear()
            self._save()

    # ── Queries ────────────────────────────────────────────────────────────

    def get_targets(self) -> list[str]:
        with self._lock:
            return sorted(self._targets)

    def is_in_scope(self, target: str) -> bool:
        normalised = self._normalise(target)
        with self._lock:
            # Direct match
            if normalised in self._targets:
                return True
            # Check if target is a subdomain of a scoped root
            for scoped in self._targets:
                if normalised.endswith("." + scoped):
                    return True
            # CIDR membership
            for scoped in self._targets:
                try:
                    network = ipaddress.ip_network(scoped, strict=False)
                    addr    = ipaddress.ip_address(normalised)
                    if addr in network:
                        return True
                except ValueError:
                    pass
            return False

    def assert_in_scope(self, target: str) -> None:
        """Raise OutOfScopeError if target is not in the declared scope."""
        if not self._targets:
            raise OutOfScopeError(
                "No targets declared in scope. Add targets via /api/combat/opsec/scope/add before performing recon."
            )
        if not self.is_in_scope(target):
            raise OutOfScopeError(
                f"Target '{target}' is outside the declared scope. "
                f"Current scope: {sorted(self._targets)}"
            )

    # ── Helpers ────────────────────────────────────────────────────────────

    @staticmethod
    def _normalise(target: str) -> str:
        """Lower-case, strip protocol prefix and trailing slashes."""
        t = target.strip().lower()
        t = re.sub(r"^https?://", "", t)
        t = t.rstrip("/")
        return t


scope_enforcer = ScopeEnforcer()
