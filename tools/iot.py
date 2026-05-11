"""IoT device control via MQTT."""

from __future__ import annotations

import json
import os

try:
    import paho.mqtt.client as mqtt
except Exception:  # pragma: no cover - optional dependency
    mqtt = None

MQTT_HOST = os.getenv("MQTT_HOST", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))

DEVICES = {
    "fan": "home/living_room/fan",
    "light": "home/living_room/light",
    "bedroom_light": "home/bedroom/light",
    "ac": "home/bedroom/ac",
}


def control_device(device: str, action: str) -> str:
    topic = DEVICES.get(device.lower())
    if not topic:
        return f"Unknown device: {device}. Options: {list(DEVICES.keys())}"
    if mqtt is None:
        return "MQTT is unavailable on this system."
    client = mqtt.Client()
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.publish(topic, json.dumps({"action": action}))
    client.disconnect()
    return f"{device} -> {action} ✓"


def list_devices() -> list[str]:
    return list(DEVICES.keys())
