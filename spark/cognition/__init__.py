"""
Spark Cognition — Thinking Layer

ONLY responsible for thinking:
- Goal Planning
- Task Decomposition
- Reasoning
- Decision Making
- Reflection
- Self Evaluation

Nothing else. No memory. No persona. No infrastructure.
"""

from spark.cognition.goal_engine import GoalEngine, Goal, Plan, Subtask
from spark.cognition.reasoning import ReasoningEngine
from spark.cognition.reflection import ReflectionEngine
from spark.cognition.planner import TaskPlanner

__all__ = [
    "GoalEngine", "Goal", "Plan", "Subtask",
    "ReasoningEngine",
    "ReflectionEngine",
    "TaskPlanner",
]
