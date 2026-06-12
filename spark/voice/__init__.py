"""
Spark Voice Loop — Always Listening

Tony Stark never types "Jarvis..."
The system is always listening.

Features:
- Wake word detection ("Jarvis", "Spark")
- Streaming STT (real-time transcription)
- Interruption handling ("Actually stop")
- Context memory across voice turns
- Natural conversation flow
"""

from spark.voice.loop import VoiceLoop

__all__ = ["VoiceLoop"]
