"""
Spark Memory — Persistent Memory System

Enhanced memory with semantic, episodic, procedural, and working types.
"""

from spark.memory.semantic import SemanticMemory
from spark.memory.episodic import EpisodicMemory
from spark.memory.procedural import ProceduralMemory
from spark.memory.working import WorkingMemory

__all__ = ["SemanticMemory", "EpisodicMemory", "ProceduralMemory", "WorkingMemory"]
