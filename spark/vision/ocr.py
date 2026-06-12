"""Vision OCR — Extract text from screenshots using multiple OCR engines."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.vision.ocr")


class VisionOCR:
    """
    Extract text from screenshots using multiple OCR backends.

    Priority: EasyOCR → Tesseract → PaddleOCR
    """

    def __init__(self) -> None:
        self._backend = None
        self._reader = None
        self._initialize_backend()

    def _initialize_backend(self) -> None:
        try:
            import easyocr
            self._backend = "easyocr"
            self._reader = easyocr.Reader(["en"], gpu=False)
            logger.info("OCR backend: EasyOCR")
            return
        except ImportError:
            pass

        try:
            import pytesseract
            self._backend = "tesseract"
            logger.info("OCR backend: Tesseract")
            return
        except ImportError:
            pass

        try:
            from paddleocr import PaddleOCR
            self._backend = "paddleocr"
            self._reader = PaddleOCR(use_angle_cls=True, lang="en", show_log=False)
            logger.info("OCR backend: PaddleOCR")
            return
        except ImportError:
            pass

        self._backend = "none"
        logger.warning("No OCR backend available")

    def extract_text(self, image_path: str) -> str:
        """Extract all text from an image."""
        if self._backend == "easyocr":
            return self._extract_easyocr(image_path)
        elif self._backend == "tesseract":
            return self._extract_tesseract(image_path)
        elif self._backend == "paddleocr":
            return self._extract_paddleocr(image_path)
        return ""

    def extract_with_positions(self, image_path: str) -> list[dict[str, Any]]:
        """Extract text with bounding box positions."""
        if self._backend == "easyocr":
            return self._extract_easyocr_detailed(image_path)
        elif self._backend == "paddleocr":
            return self._extract_paddleocr_detailed(image_path)
        return [{"text": self.extract_text(image_path), "position": None}]

    def _extract_easyocr(self, image_path: str) -> str:
        try:
            results = self._reader.readtext(image_path)
            texts = [r[1] for r in results]
            return "\n".join(texts)
        except Exception as exc:
            logger.error("EasyOCR failed: %s", exc)
            return ""

    def _extract_easyocr_detailed(self, image_path: str) -> list[dict[str, Any]]:
        try:
            results = self._reader.readtext(image_path)
            return [
                {"text": r[1], "confidence": float(r[2]), "position": r[0]}
                for r in results
            ]
        except Exception:
            return []

    def _extract_tesseract(self, image_path: str) -> str:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(image_path)
            return pytesseract.image_to_string(img)
        except Exception as exc:
            logger.error("Tesseract failed: %s", exc)
            return ""

    def _extract_paddleocr(self, image_path: str) -> str:
        try:
            result = self._reader.ocr(image_path, cls=True)
            texts = [line[1][0] for line in result[0]] if result and result[0] else []
            return "\n".join(texts)
        except Exception as exc:
            logger.error("PaddleOCR failed: %s", exc)
            return ""

    @property
    def backend(self) -> str:
        return self._backend
