"""Camera Stream — Video input for visual awareness."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.multimodal.camera")


class CameraStream:
    """Camera input for visual awareness."""

    def __init__(self) -> None:
        self._active = False
        self._last_frame: str | None = None

    def start(self) -> bool:
        try:
            import cv2
            self._cap = cv2.VideoCapture(0)
            if self._cap.isOpened():
                self._active = True
                logger.info("Camera stream started")
                return True
        except ImportError:
            logger.warning("opencv-python not installed")
        except Exception as exc:
            logger.error("Camera start failed: %s", exc)
        return False

    def capture_frame(self) -> str | None:
        if not self._active:
            return None
        try:
            import cv2
            ret, frame = self._cap.read()
            if ret:
                path = f"spark_dev_memory/camera/frame_{int(time.time()*1000)}.jpg"
                cv2.imwrite(path, frame)
                self._last_frame = path
                return path
        except Exception as exc:
            logger.warning("Frame capture failed: %s", exc)
        return None

    def stop(self) -> None:
        if hasattr(self, '_cap'):
            self._cap.release()
        self._active = False
        logger.info("Camera stream stopped")

    @property
    def is_active(self) -> bool:
        return self._active
