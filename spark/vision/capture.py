"""Screen Capture — Real screen capture using MSS, DXCam, PyAutoGUI."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.vision.capture")


class ScreenCapture:
    """
    Real screen capture using multiple backends.

    Priority: DXCam (fastest) → MSS → PyAutoGUI (fallback)
    """

    def __init__(self, output_dir: str = "spark_dev_memory/screenshots") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)
        self._backend = None
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        try:
            import dxcam
            self._backend = "dxcam"
            self._camera = dxcam.create(output_color="BGR")
            logger.info("Screen capture backend: DXCam")
            return
        except ImportError:
            pass

        try:
            import mss
            self._backend = "mss"
            self._sct = mss.mss()
            logger.info("Screen capture backend: MSS")
            return
        except ImportError:
            pass

        try:
            import pyautogui
            self._backend = "pyautogui"
            logger.info("Screen capture backend: PyAutoGUI")
            return
        except ImportError:
            pass

        self._backend = "none"
        logger.warning("No screen capture backend available")

    def capture(self, region: tuple[int, int, int, int] | None = None) -> str | None:
        """Capture screen and return path to screenshot."""
        timestamp = int(time.time() * 1000)
        output_path = self._output_dir / f"screen_{timestamp}.png"

        try:
            if self._backend == "dxcam":
                return self._capture_dxcam(output_path, region)
            elif self._backend == "mss":
                return self._capture_mss(output_path, region)
            elif self._backend == "pyautogui":
                return self._capture_pyautogui(output_path)
        except Exception as exc:
            logger.error("Capture failed: %s", exc)
        return None

    def _capture_dxcam(self, output_path: Path, region: tuple | None) -> str:
        import numpy as np
        from PIL import Image
        if region:
            image = self._camera.grab(region)
        else:
            image = self._camera.grab()
        if image is None:
            return ""
        Image.fromarray(image).save(str(output_path))
        return str(output_path)

    def _capture_mss(self, output_path: Path, region: tuple | None) -> str:
        from PIL import Image
        if region:
            monitor = {"left": region[0], "top": region[1], "width": region[2], "height": region[3]}
        else:
            monitor = self._sct.monitors[0]
        screenshot = self._sct.grab(monitor)
        Image.frombytes("RGB", screenshot.size, screenshot.bgra, "raw", "BGRX").save(str(output_path))
        return str(output_path)

    def _capture_pyautogui(self, output_path: Path) -> str:
        import pyautogui
        screenshot = pyautogui.screenshot()
        screenshot.save(str(output_path))
        return str(output_path)

    def capture_region(self, x: int, y: int, width: int, height: int) -> str | None:
        return self.capture(region=(x, y, width, height))

    def capture_active_window(self) -> str | None:
        try:
            import pygetwindow as gw
            win = gw.getActiveWindow()
            if win:
                return self.capture(region=(win.left, win.top, win.width, win.height))
        except Exception:
            pass
        return self.capture()

    @property
    def backend(self) -> str:
        return self._backend

    def info(self) -> dict[str, Any]:
        return {
            "backend": self._backend,
            "output_dir": str(self._output_dir),
        }
