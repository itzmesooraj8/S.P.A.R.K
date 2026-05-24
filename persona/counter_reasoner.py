from __future__ import annotations

class MoralCounterReasoner:
    """Algorithmic safety checker that prevents execution of commands violating safety profiles."""
    def __init__(self, blocked_actions: set[str] | None = None):
        if blocked_actions is None:
            self.blocked_actions = {
                "delete_all_files", 
                "disable_security_checks", 
                "override_hardware_fans",
                "bypass_authentication",
                "force_unlocked_state"
            }
        else:
            self.blocked_actions = blocked_actions

    def validate_action(self, action_name: str) -> tuple[bool, str]:
        """Checks target action against safety protocols. Returns (is_allowed, counter_argument)."""
        if action_name in self.blocked_actions:
            counter = (
                f"Sir, I cannot execute '{action_name}'. Disabling safety limits or removing critical "
                f"system components poses a security risk to this machine's kernel health."
            )
            return False, counter
        return True, ""
