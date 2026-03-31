"""
WiFi-DensePose WebSocket Bridge
================================
Connects to a local WiFi-DensePose inference server (e.g. ruvnet/wifi-densepose)
and forwards physical-presence frames parsed from router WiFi signals to SPARK's 'combat' WebSocket namespace
for rendering in the SENSOR tab of the SentinelModule.

The inference server exposes:
  ws://<host>:<port>/ws  →  JSON frames:
    {
      "persons": [
        {
          "id": 1,
          "bbox": [x1,y1,x2,y2],
          "keypoints": [[x,y,c], ...],   // 17 COCO keypoints
          "heart_rate": 72,              // BPM estimate (if model supports)
          "action": "standing"            // action label
        }
      ],
      "timestamp": 1710000000.0,
      "rssi": -65
    }
"""
import asyncio
import json
import logging
import time
from typing import TypedDict, List, Optional

log = logging.getLogger(__name__)

try:
    import websockets  # type: ignore
    _WS_OK = True
except ImportError:
    _WS_OK = False
    log.warning("websockets not installed — DensePose client disabled")


class SensorFrame(TypedDict):
    timestamp:    float
    person_count: int
    persons:      list
    rssi:         Optional[int]


class DensePoseClient:
    """
    Background task that bridges a local DensePose WS server → SPARK combat WS.
    """

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host    = host
        self.port    = port
        self._task: Optional[asyncio.Task] = None
        self._running = False

    @property
    def url(self) -> str:
        return f"ws://{self.host}:{self.port}/ws"

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._bridge_loop(), name="wifi_densepose_bridge")
        log.info("WiFi-DensePose Bridge Started [Router Sniffing Active] → %s", self.url)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            self._task = None
        log.info("DensePose bridge stopped")

    async def _bridge_loop(self) -> None:
        from spark_core.ws.manager import ws_manager

        while self._running:
            try:
                if not _WS_OK:
                    # Mock mode: emit a synthetic person every 2 seconds
                    await self._mock_loop(ws_manager)
                    return

                async with websockets.connect(self.url, max_size=2**20) as ws:
                    log.info("DensePose: connected to %s", self.url)
                    async for raw in ws:
                        if not self._running:
                            break
                        try:
                            data = json.loads(raw)
                            frame = SensorFrame(
                                timestamp    = data.get("timestamp", time.time()),
                                person_count = len(data.get("persons", [])),
                                persons      = data.get("persons", []),
                                rssi         = data.get("rssi"),
                            )
                            await ws_manager.broadcast("combat", {
                                "type":  "SENSOR_FRAME",
                                "frame": frame,
                            })
                        except (json.JSONDecodeError, KeyError) as e:
                            log.debug("DensePose frame parse error: %s", e)
            except (ConnectionRefusedError, OSError) as e:
                log.warning("DensePose server not reachable (%s) — retrying in 5s", e)
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break
            except Exception as e:
                log.error("DensePose bridge error: %s", e)
                await asyncio.sleep(5)

    async def _mock_loop(self, ws_manager) -> None:
        """Emit synthetic frames every 2 seconds when websockets unavailable (WiFi-DensePose Simulation)."""
        import random
        person_id = 1
        while self._running:
            await asyncio.sleep(2)
            frame = SensorFrame(
                timestamp    = time.time(),
                person_count = 1,
                persons      = [{
                    "id":     person_id,
                    "bbox":   [100, 50, 300, 450],
                    "action": random.choice(["standing", "walking", "sitting"]),
                    "heart_rate": random.randint(60, 100),
                    "keypoints": [],
                }],
                rssi = random.randint(-80, -40),
            )
            await ws_manager.broadcast("combat", {
                "type":  "SENSOR_FRAME",
                "frame": frame,
            })


# Global singleton
_densepose_client: Optional[DensePoseClient] = None


def get_densepose_client() -> Optional[DensePoseClient]:
    return _densepose_client


async def connect_densepose(host: str = "localhost", port: int = 8765) -> DensePoseClient:
    global _densepose_client
    if _densepose_client and _densepose_client._running:
        await _densepose_client.stop()
    _densepose_client = DensePoseClient(host=host, port=port)
    await _densepose_client.start()
    return _densepose_client
