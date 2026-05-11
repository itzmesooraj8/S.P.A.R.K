"""Screen reader - SPARK can see what's on your screen."""

from __future__ import annotations

import os

try:
    from PIL import ImageGrab
    import pytesseract
except Exception:  # pragma: no cover - optional dependency
    ImageGrab = None  # type: ignore[assignment]
    pytesseract = None  # type: ignore[assignment]

if os.name == "nt" and pytesseract is not None:
    default_path = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    if os.path.exists(default_path):
        pytesseract.pytesseract.tesseract_cmd = default_path


def read_screen() -> str:
    """Take a screenshot and extract all text via OCR."""
    try:
        if ImageGrab is None or pytesseract is None:
            return "Screen OCR dependencies are not installed."
        screenshot = ImageGrab.grab()
        text = pytesseract.image_to_string(screenshot)
        return text.strip() if text.strip() else "Nothing readable on screen."
    except Exception as exc:
        return f"Screen read error: {exc}"


def read_region(x1: int, y1: int, x2: int, y2: int) -> str:
    """Read a specific region of the screen."""
    try:
        if ImageGrab is None or pytesseract is None:
            return "Screen OCR dependencies are not installed."
        region = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        return pytesseract.image_to_string(region).strip()
    except Exception as exc:
        return f"Region read error: {exc}"


def get_screen_dimensions() -> dict:
    """Return screen width and height."""
    try:
        if ImageGrab is None:
            return {"error": "Screen capture dependencies are not installed."}
        screen = ImageGrab.grab()
        return {"width": screen.width, "height": screen.height}
    except Exception as exc:
        return {"error": str(exc)}
