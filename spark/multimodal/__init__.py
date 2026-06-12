"""
Spark Multi-Modal — Camera, Microphone, Sensor Streams

Version 3.0 feature — not required for v2.0 but builds toward full JARVIS.
"""

from spark.multimodal.camera import CameraStream
from spark.multimodal.microphone import MicrophoneStream
from spark.multimodal.sensor import SensorHub

__all__ = ["CameraStream", "MicrophoneStream", "SensorHub"]
