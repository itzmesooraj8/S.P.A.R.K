"""
Spark Persona — Identity Layer

ONLY responsible for identity:
- Communication Style
- Preferences
- Tone
- Personality
- Behavior Settings

Persona should never contain reasoning.
"""

from spark.persona.identity import PersonaIdentity
from spark.persona.style import CommunicationStyle

__all__ = ["PersonaIdentity", "CommunicationStyle"]
