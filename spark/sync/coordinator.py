"""Device Coordinator — Cross-device synchronization."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.sync.coordinator")


class DeviceState:
    def __init__(self, device_id: str, device_type: str):
        self.device_id = device_id
        self.device_type = device_type
        self.last_seen = time.time()
        self.state: dict[str, Any] = {}
        self.active = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "last_seen": self.last_seen,
            "state": self.state,
            "active": self.active,
        }


class DeviceCoordinator:
    """
    Cross-device synchronization.

    All devices share:
    - Working memory
    - Active goals
    - Current context
    - Conversation state
    """

    def __init__(self, storage_path: str = "spark_dev_memory/devices.json") -> None:
        self._path = Path(storage_path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._devices: dict[str, DeviceState] = {}
        self._shared_state: dict[str, Any] = {
            "working_memory": {},
            "active_goals": [],
            "current_context": {},
            "conversation": [],
        }
        self._sync_log: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                data = json.loads(self._path.read_text(encoding="utf-8"))
                self._shared_state = data.get("shared_state", self._shared_state)
            except Exception:
                pass

    def _save(self) -> None:
        data = {
            "devices": {k: v.to_dict() for k, v in self._devices.items()},
            "shared_state": self._shared_state,
            "updated_at": time.time(),
        }
        self._path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    def register_device(self, device_id: str, device_type: str) -> None:
        self._devices[device_id] = DeviceState(device_id, device_type)
        self._save()
        logger.info("Device registered: %s (%s)", device_id, device_type)

    def update_device_state(self, device_id: str, state: dict[str, Any]) -> None:
        if device_id in self._devices:
            self._devices[device_id].state.update(state)
            self._devices[device_id].last_seen = time.time()
            self._save()

    def sync_state(self, source_device: str, state_key: str, value: Any) -> None:
        self._shared_state[state_key] = value
        self._sync_log.append({
            "source": source_device,
            "key": state_key,
            "timestamp": time.time(),
        })
        if len(self._sync_log) > 100:
            self._sync_log = self._sync_log[-100:]
        self._save()

    def get_synced_state(self, state_key: str) -> Any:
        return self._shared_state.get(state_key)

    def get_active_devices(self) -> list[dict[str, Any]]:
        now = time.time()
        for device in self._devices.values():
            device.active = (now - device.last_seen) < 300
        return [d.to_dict() for d in self._devices.values() if d.active]

    def get_all_devices(self) -> list[dict[str, Any]]:
        return [d.to_dict() for d in self._devices.values()]

    def broadcast(self, message: str, exclude_device: str | None = None) -> dict[str, Any]:
        sent = []
        for device_id, device in self._devices.items():
            if device_id != exclude_device and device.active:
                sent.append(device_id)
        return {"broadcast": True, "sent_to": sent, "message": message}

    def snapshot(self) -> dict[str, Any]:
        return {
            "devices": self.get_all_devices(),
            "shared_state": self._shared_state,
            "sync_log": self._sync_log[-10:],
        }
