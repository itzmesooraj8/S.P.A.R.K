"""
Spark Awareness — Environment Perception

- Screen Awareness
- Application Awareness
- Context Awareness
- User Activity Awareness
- Environment Awareness
- Awareness Bus (continuous event publishing)
- World Model (understands user behavior)
"""

from spark.awareness.screen import ScreenAwareness
from spark.awareness.application import ApplicationAwareness
from spark.awareness.context import ContextAwareness
from spark.awareness.user import UserAwareness
from spark.awareness.environment import EnvironmentAwareness
from spark.awareness.bus import AwarenessBus
from spark.awareness.world_model import WorldModel

__all__ = [
    "ScreenAwareness",
    "ApplicationAwareness",
    "ContextAwareness",
    "UserAwareness",
    "EnvironmentAwareness",
    "AwarenessBus",
    "WorldModel",
]
