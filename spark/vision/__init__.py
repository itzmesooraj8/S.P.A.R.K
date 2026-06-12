"""
Spark Vision — Real Screen Capture + OCR + Vision Model Understanding

This is what makes SPARK actually SEE like JARVIS.

Not just "VS Code opened" but:
- User is debugging Python code
- User is reading FastAPI documentation
- User is reviewing a pull request
"""

from spark.vision.capture import ScreenCapture
from spark.vision.ocr import VisionOCR
from spark.vision.understand import VisionUnderstander

__all__ = ["ScreenCapture", "VisionOCR", "VisionUnderstander"]
