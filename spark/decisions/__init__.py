"""
Spark Decisions — Decision Log

Extremely important for debugging.
Why did SPARK do this?
Without this, debugging becomes impossible.
"""

from spark.decisions.log import DecisionLog, Decision

__all__ = ["DecisionLog", "Decision"]
