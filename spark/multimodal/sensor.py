"""Sensor Hub — IoT and environmental sensor aggregation."""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("spark.multimodal.sensor")


class SensorReading:
    def __init__(self, sensor_type: str, value: Any, unit: str = ""):
        self.sensor_type = sensor_type
        self.value = value
        self.unit = unit
        self.timestamp = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.sensor_type, "value": self.value, "unit": self.unit, "timestamp": self.timestamp}


class SensorHub:
    """Aggregates data from multiple sensors."""

    def __init__(self) -> None:
        self._sensors: dict[str, dict[str, Any]] = {}
        self._readings: list[SensorReading] = []

    def register_sensor(self, sensor_id: str, sensor_type: str, metadata: dict[str, Any] | None = None) -> None:
        self._sensors[sensor_id] = {"type": sensor_type, "metadata": metadata or {}, "last_reading": 0.0}

    def add_reading(self, sensor_id: str, value: Any, unit: str = "") -> None:
        if sensor_id not in self._sensors:
            return
        sensor_type = self._sensors[sensor_id]["type"]
        reading = SensorReading(sensor_type, value, unit)
        self._readings.append(reading)
        self._sensors[sensor_id]["last_reading"] = time.time()
        if len(self._readings) > 1000:
            self._readings = self._readings[-1000:]

    def get_latest(self, sensor_type: str | None = None) -> list[dict[str, Any]]:
        readings = self._readings if sensor_type is None else [r for r in self._readings if r.sensor_type == sensor_type]
        return [r.to_dict() for r in readings[-10:]]

    def get_all_sensors(self) -> list[dict[str, Any]]:
        return [{"id": k, **v} for k, v in self._sensors.items()]

    def snapshot(self) -> dict[str, Any]:
        return {"sensors": self.get_all_sensors(), "recent_readings": self.get_latest()}
