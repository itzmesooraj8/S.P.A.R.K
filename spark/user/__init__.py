"""
Spark User Model — Learns Everything About the User

Without this, SPARK remains generic.

It learns:
- Preferred tools
- Preferred coding style
- Work schedule
- Projects
- Goals
- Habits
- Communication preferences
"""

from spark.user.model import UserModel

__all__ = ["UserModel"]
