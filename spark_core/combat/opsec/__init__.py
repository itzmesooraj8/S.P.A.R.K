"""OpSec layer — VPN/Tor detection, scope enforcement, encrypted vault."""
from .vpn_check import run_vpn_check
from .scope_enforcer import scope_enforcer, OutOfScopeError
from .vault import combat_vault

__all__ = ["run_vpn_check", "scope_enforcer", "OutOfScopeError", "combat_vault"]
