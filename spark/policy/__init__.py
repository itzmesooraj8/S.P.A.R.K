"""
Spark Policy Engine — Constitution for autonomous actions.

Every action passes policy.evaluate() before execution.
Similar to OPA/Guardrails/Rego.
"""

from spark.policy.engine import PolicyEngine, PolicyRule

__all__ = ["PolicyEngine", "PolicyRule"]
