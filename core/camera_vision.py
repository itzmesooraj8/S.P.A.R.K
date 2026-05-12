from __future__ import annotations

import logging
from pathlib import Path
from typing import Any


log = logging.getLogger("spark.camera_vision")

_cv2 = None
_YOLO = None
_camera_model = None


def _load_dependencies() -> tuple[Any, Any] | None:
    global _cv2, _YOLO
    if _cv2 is not None and _YOLO is not None:
        return _cv2, _YOLO

    try:
        import cv2
        from ultralytics import YOLO
    except Exception as exc:
        log.info("Camera vision unavailable: %s", exc)
        return None

    _cv2 = cv2
    _YOLO = YOLO
    return _cv2, _YOLO


def capture_camera_frame(output_path: str | Path = "spark_dev_memory/camera/latest_frame.jpg") -> str:
    deps = _load_dependencies()
    if deps is None:
        return "Camera vision unavailable: OpenCV/Ultralytics not installed."

    cv2, _ = deps
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        return "Camera unavailable: could not open webcam."

    try:
        ok, frame = cap.read()
        if not ok or frame is None:
            return "Camera unavailable: no frame captured."
        cv2.imwrite(str(output), frame)
        return str(output)
    finally:
        cap.release()


def analyze_camera_frame(frame_path: str | Path | None = None) -> str:
    deps = _load_dependencies()
    if deps is None:
        return "Camera vision unavailable: OpenCV/Ultralytics not installed."

    _, YOLO = deps
    path = Path(frame_path or "spark_dev_memory/camera/latest_frame.jpg")
    if not path.exists():
        captured = capture_camera_frame(path)
        if captured != str(path):
            return captured

    global _camera_model
    if _camera_model is None:
        try:
            _camera_model = YOLO("yolov8n.pt")
        except Exception as exc:
            return f"Camera vision unavailable: could not load YOLOv8 model ({exc})."

    try:
        results = _camera_model.predict(source=str(path), imgsz=640, device="cpu", verbose=False)
        labels: list[str] = []
        for result in results:
            boxes = getattr(result, "boxes", None)
            if boxes is None:
                continue
            names = result.names if hasattr(result, "names") else {}
            for box in boxes:
                cls_value = getattr(box, "cls", None)
                conf_value = getattr(box, "conf", None)
                cls_id = int(cls_value[0]) if hasattr(cls_value, "__getitem__") else int(cls_value)
                label = str(names.get(cls_id, f"class_{cls_id}"))
                confidence = float(conf_value[0]) if hasattr(conf_value, "__getitem__") else float(conf_value)
                labels.append(f"{label} ({confidence:.2f})")

        if not labels:
            return "No obvious objects detected in the camera frame."
        return "Detected: " + ", ".join(labels[:10])
    except Exception as exc:
        return f"Camera analysis failed: {exc}"
