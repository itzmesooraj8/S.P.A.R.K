"""IoT Controller — Home automation via MQTT, Home Assistant, Zigbee."""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

logger = logging.getLogger("spark.automation.iot")


class IoTDevice:
    def __init__(self, device_id: str, name: str, device_type: str, state: dict[str, Any] | None = None):
        self.device_id = device_id
        self.name = name
        self.device_type = device_type
        self.state = state or {}
        self.available = True

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.device_id, "name": self.name, "type": self.device_type, "state": self.state, "available": self.available}


class IoTController:
    """
    IoT device control via MQTT, Home Assistant, or direct API.

    Supports:
    - MQTT (via paho-mqtt)
    - Home Assistant REST API
    - Direct HTTP/CoAP
    """

    def __init__(self, backend: str = "mqtt", config: dict[str, Any] | None = None) -> None:
        self._backend = backend
        self._config = config or {}
        self._devices: dict[str, IoTDevice] = {}
        self._mqtt_client = None
        self._callbacks: dict[str, Callable] = {}

    async def connect(self) -> bool:
        if self._backend == "mqtt":
            return await self._connect_mqtt()
        elif self._backend == "home_assistant":
            return await self._connect_ha()
        return False

    async def _connect_mqtt(self) -> bool:
        try:
            import paho.mqtt.client as mqtt
            self._mqtt_client = mqtt.Client()
            host = self._config.get("mqtt_host", "localhost")
            port = self._config.get("mqtt_port", 1883)
            self._mqtt_client.connect(host, port)
            self._mqtt_client.loop_start()
            logger.info("MQTT connected to %s:%d", host, port)
            return True
        except ImportError:
            logger.error("paho-mqtt not installed: pip install paho-mqtt")
            return False
        except Exception as exc:
            logger.error("MQTT connect failed: %s", exc)
            return False

    async def _connect_ha(self) -> bool:
        self._ha_url = self._config.get("ha_url", "http://localhost:8123")
        self._ha_token = self._config.get("ha_token", "")
        if not self._ha_token:
            logger.warning("Home Assistant token not set")
            return False
        logger.info("Home Assistant configured at %s", self._ha_url)
        return True

    def register_device(self, device: IoTDevice) -> None:
        self._devices[device.device_id] = device
        logger.info("IoT device registered: %s (%s)", device.name, device.device_type)

    async def turn_on(self, device_id: str) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"success": False, "error": f"Device not found: {device_id}"}
        return await self._send_command(device, "turn_on", {})

    async def turn_off(self, device_id: str) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"success": False, "error": f"Device not found: {device_id}"}
        return await self._send_command(device, "turn_off", {})

    async def set_state(self, device_id: str, state: dict[str, Any]) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"success": False, "error": f"Device not found: {device_id}"}
        return await self._send_command(device, "set_state", state)

    async def get_state(self, device_id: str) -> dict[str, Any]:
        device = self._devices.get(device_id)
        if not device:
            return {"success": False, "error": f"Device not found: {device_id}"}
        return {"success": True, "state": device.state}

    async def _send_command(self, device: IoTDevice, command: str, params: dict[str, Any]) -> dict[str, Any]:
        if self._backend == "mqtt":
            return self._mqtt_publish(device, command, params)
        elif self._backend == "home_assistant":
            return await self._ha_call(device, command, params)
        return {"success": False, "error": "No backend connected"}

    def _mqtt_publish(self, device: IoTDevice, command: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._mqtt_client:
            return {"success": False, "error": "MQTT not connected"}
        topic = f"spark/iot/{device.device_id}/{command}"
        payload = json.dumps(params)
        self._mqtt_client.publish(topic, payload)
        device.state.update(params)
        return {"success": True, "device": device.name, "command": command}

    async def _ha_call(self, device: IoTDevice, command: str, params: dict[str, Any]) -> dict[str, Any]:
        try:
            import httpx
            domain = "light" if "light" in device.device_type else "switch"
            action = "turn_on" if command == "turn_on" else "turn_off"
            url = f"{self._ha_url}/api/services/{domain}/{action}"
            headers = {"Authorization": f"Bearer {self._ha_token}", "Content-Type": "application/json"}
            data = {"entity_id": device.device_id, **params}
            async with httpx.AsyncClient() as client:
                r = await client.post(url, headers=headers, json=data)
                return {"success": r.status_code == 200, "device": device.name}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def list_devices(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._devices.values()]

    async def disconnect(self) -> None:
        if self._mqtt_client:
            self._mqtt_client.loop_stop()
            self._mqtt_client.disconnect()
