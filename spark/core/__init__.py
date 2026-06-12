"""
Spark Core — Infrastructure Layer

ONLY responsible for infrastructure:
- Event Bus (pub/sub system)
- State Management (system state tracking)
- Dependency Injection (service registry)
- Configuration (settings management)
- Registry (component registration)

No AI logic. No persona logic. No reasoning.
"""

from spark.core.events import EventBus, Event
from spark.core.state import StateManager
from spark.core.config import SparkConfig
from spark.core.registry import Registry
from spark.core.container import Container

__all__ = [
    "EventBus", "Event",
    "StateManager",
    "SparkConfig",
    "Registry",
    "Container",
]
