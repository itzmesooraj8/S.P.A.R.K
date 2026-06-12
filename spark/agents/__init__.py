"""
Spark Agents — Specialized Agent Framework

- Planner Agent
- Executor Agent
- Memory Agent
- Reflection Agent
- Observer Agent
"""

from spark.agents.base import BaseAgent, AgentStatus
from spark.agents.planner import PlannerAgent
from spark.agents.executor import ExecutorAgent
from spark.agents.memory_agent import MemoryAgent
from spark.agents.reflection_agent import ReflectionAgent
from spark.agents.observer import ObserverAgent

__all__ = [
    "BaseAgent", "AgentStatus",
    "PlannerAgent", "ExecutorAgent", "MemoryAgent",
    "ReflectionAgent", "ObserverAgent",
]
