"""
Spark Reliability — Risk Engine, Retry Logic, Failure Recovery, Self-Correction

The difference between:
Automation Framework
and
Autonomous Digital Worker
is reliability.

Can it recover from UI changes?
Can it retry intelligently?
Can it explain failures?
Can it self-correct?
"""

from spark.reliability.risk import RiskEngine
from spark.reliability.retry import RetryManager
from spark.reliability.recovery import FailureRecovery

__all__ = ["RiskEngine", "RetryManager", "FailureRecovery"]
