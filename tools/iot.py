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

_SONOFF_PLUG_TOPIC = os.getenv("SONOFF_PLUG_TOPIC", "").strip()


def control_device(device: str, action: str) -> str:
    """Connect once, publish a device action, and disconnect."""
    topic = DEVICES.get(device.lower())
    if not topic:
        return f"Unknown device: {device}. Options: {list(DEVICES.keys())}"
    if mqtt is None:
        return "MQTT is unavailable on this system."
    client = mqtt.Client()
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.publish(topic, json.dumps({"action": action}))
        client.disconnect()
        return f"{device} → {action} ✓"
    except Exception as exc:
        return f"MQTT error: {exc}"


def list_devices() -> list[str]:
    """Return the available smart home device names."""
    return list(DEVICES.keys())


def control_smart_plug(action: str) -> str:
    """Convenience helper for a single Sonoff-style plug on MQTT."""
    if mqtt is None:
        return "MQTT is unavailable on this system."
    if not _SONOFF_PLUG_TOPIC:
        return "Smart plug control is disabled. Set SONOFF_PLUG_TOPIC to enable it."

    client = mqtt.Client()
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        client.publish(_SONOFF_PLUG_TOPIC, json.dumps({"action": action}))
        client.disconnect()
        return f"smart_plug → {action} ✓"
    except Exception as exc:
        return f"MQTT error: {exc}"
