"""S.P.A.R.K. API Startup and Service Lifecycle Registry."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import threading
import time
from typing import Any

import requests
import numpy as np

logger = logging.getLogger("SPARK_STARTUP")

# Shared state/globals
_broadcast_loop: asyncio.AbstractEventLoop | None = None
tunnel_proc: subprocess.Popen | None = None


class TelemetryRefresher:
    """Thread-safe background telemetry refresher running at 10 Hz."""

    def __init__(self, orchestrator=None, classifier=None):
        self.orchestrator = orchestrator
        self.classifier = classifier
        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    def start(self, broadcast_fn=None):
        with self._lock:
            if self._thread is None:
                self._running = True
                self._thread = threading.Thread(
                    target=self._loop,
                    args=(broadcast_fn,),
                    daemon=True,
                    name="spark-telemetry-refresher",
                )
                self._thread.start()
                logger.info("TelemetryRefresher background thread started.")

    def stop(self):
        with self._lock:
            self._running = False
            self._thread = None
            logger.info("TelemetryRefresher background thread stopped.")

    def _loop(self, broadcast_fn):
        if broadcast_fn is None:
            def default_broadcast(payload):
                try:
                    from api.server import broadcast_system_alert
                    broadcast_system_alert(payload)
                except Exception as e:
                    logger.debug("Failed to fallback to api.server.broadcast_system_alert: %s", e)
            broadcast_fn = default_broadcast

        try:
            from network.swarm_orchestrator import SwarmOrchestrator
            from diagnostics.industrial_diagnostics import IndustrialTelemetryClassifier
        except Exception as e:
            logger.error("Failed to import telemetry/diagnostics dependencies: %s", e)
            return

        orch = self.orchestrator
        if orch is None:
            try:
                orch = SwarmOrchestrator()
                orch.start()
            except Exception as e:
                logger.warning("SwarmOrchestrator could not be started: %s", e)

        classif = self.classifier or IndustrialTelemetryClassifier()

        while self._running:
            try:
                node_drops = 0
                packet_loss = 0.0
                routing_state = "cloud_preferred"
                if orch:
                    snapshot = orch.get_cluster_snapshot()
                    routing_state = snapshot.get("routing_state", "cloud_preferred")
                    nodes = snapshot.get("nodes", {})
                    for ip, n in nodes.items():
                        if not n.get("healthy", False):
                            node_drops += 1
                        packet_loss = max(packet_loss, n.get("drop_rate", 0.0))

                t = np.linspace(0.0, 1.0, 128)
                signal = np.vstack([
                    np.sin(2 * np.pi * 10 * t) + 0.1 * np.random.randn(128),
                    np.cos(2 * np.pi * 20 * t) + 0.1 * np.random.randn(128),
                    np.sin(2 * np.pi * 50 * t) + 0.1 * np.random.randn(128),
                ])
                diag_res = classif.classify(signal)

                payload = {
                    "type": "swarm_heartbeat",
                    "timestamp": time.time(),
                    "computation_node_drops": node_drops,
                    "packet_loss": packet_loss,
                    "routing_state": routing_state,
                    "vibration_prediction": diag_res.get("prediction", "nominal"),
                    "vibration_confidence": diag_res.get("confidence", 1.0),
                    "class_probabilities": diag_res.get("class_probabilities", {}),
                }

                broadcast_fn(payload)

            except Exception as exc:
                logger.error("Error in TelemetryRefresher loop: %s", exc)

            time.sleep(0.1)


telemetry_refresher = TelemetryRefresher()


def broadcast_system_alert(alert_payload: dict[str, Any], manager_broadcast_fn) -> None:
    """Broadcasts a system-wide alert or warning to all active websocket terminals."""
    if alert_payload.get("type") == "swarm_heartbeat":
        msg_str = (
            f"[TELEMETRY 10Hz] Node Drops: {alert_payload.get('computation_node_drops')} | "
            f"Packet Loss: {alert_payload.get('packet_loss'):.2f} | "
            f"Prediction: {alert_payload.get('vibration_prediction')} ({alert_payload.get('vibration_confidence'):.2f})"
        )
        logger.info(msg_str)
    else:
        logger.warning("SYSTEM ALERT BROADCAST: %s", alert_payload)

    msg = {
        "type": "system_alert",
        "payload": alert_payload,
        "timestamp": time.time(),
    }
    try:
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        target_loop = running_loop or _broadcast_loop
        if target_loop and not target_loop.is_closed():
            if running_loop is target_loop:
                target_loop.create_task(manager_broadcast_fn(msg))
            else:
                asyncio.run_coroutine_threadsafe(manager_broadcast_fn(msg), target_loop)
        else:
            logger.warning("No active event loop available for alert broadcast: %s", alert_payload)
    except Exception as exc:
        logger.error("Failed to spawn thread for alert broadcast: %s", exc)


async def execute_startup_sequence(vitals_router, manager_broadcast_fn) -> None:
    """Initializes and runs all background daemons in proper order."""
    global _broadcast_loop, tunnel_proc
    _broadcast_loop = asyncio.get_running_loop()

    # 1. Start Vitals Monitoring Daemon
    try:
        vitals_router.start_daemon()
        logger.info("Vitals daemon started in background thread.")
    except Exception as exc:
        logger.warning(f"Vitals daemon failed to start: {exc}")

    # 2. Start Audio Isolation Daemon
    try:
        from api.audio_daemon import audio_daemon_instance
        audio_daemon_instance.start()
        logger.info("Audio isolation daemon started on startup.")
    except Exception as exc:
        logger.warning(f"Audio isolation daemon failed to start: {exc}")

    # 3. Preload Whisper model in executor
    try:
        from tools.voice import load_whisper
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, load_whisper)
        logger.info("Whisper model preloaded successfully.")
    except Exception as exc:
        logger.warning(f"Whisper preload failed: {exc}")

    # 4. Start Scheduler, Perception, Heartbeat
    try:
        from core.scheduler import init_scheduler
        init_scheduler()
    except Exception as exc:
        logger.warning(f"Scheduler startup failed: {exc}")

    try:
        from core.perception import start_ambient_perception
        start_ambient_perception()
    except Exception as exc:
        logger.warning(f"Ambient perception startup failed: {exc}")

    try:
        from core.heartbeat import start_heartbeat
        start_heartbeat()
    except Exception as exc:
        logger.warning(f"Heartbeat startup failed: {exc}")

    # 5. Local brain chain warm-up in a separate thread
    try:
        from core.local_brain_chain import warmup_chain
        threading.Thread(target=warmup_chain, daemon=True, name="spark-brain-warmup").start()
        logger.info("Local brain chain warm-up started in background.")
    except Exception as exc:
        logger.warning(f"Local brain warmup failed to start: {exc}")

    # 6. Start Takeover Mode
    try:
        from core.takeover import start_takeover_mode
        start_takeover_mode()
    except Exception as exc:
        logger.warning(f"Takeover startup failed: {exc}")

    # 7. Start Wake Engine
    _wake_lock = threading.Lock()

    def on_wake():
        if not _wake_lock.acquire(blocking=False):
            return  # already processing, skip
        try:
            from api.auth import get_static_operator_token
            resp = requests.post(
                "http://localhost:8000/listen",
                headers={"Authorization": f"Bearer {get_static_operator_token()}"},
                timeout=30,
            )
            reply = resp.json().get("reply", "")
            logger.info("Wake handler reply: %s", reply)
        except Exception as exc:
            logger.error("Wake handler error: %s", exc, exc_info=True)
        finally:
            _wake_lock.release()

    try:
        from core.wake_word import start_wake_engine
        use_hotword = os.getenv("SPARK_ENABLE_HOTWORD", "1").strip().lower() in {"1", "true", "yes", "on"}
        start_wake_engine(on_wake_callback=on_wake, use_hotword=use_hotword)
    except Exception as exc:
        logger.warning(f"Wake engine startup failed: {exc}")

    # 8. Start Cloudflare Tunnel if enabled
    enable_tunnel = os.getenv("SPARK_ENABLE_TUNNEL", "0").strip().lower() in {"1", "true", "yes", "on"}
    if enable_tunnel:
        try:
            tunnel_proc = subprocess.Popen(
                ["cloudflared", "tunnel", "--url", "http://localhost:8000"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            time.sleep(2)
            logger.info("[SPARK] Cloudflare tunnel starting for remote Signal Override")
        except Exception as exc:
            logger.warning(f"Cloudflare tunnel startup failed: {exc}")

    # 9. Start Swarm Telemetry 10Hz Refresher
    try:
        telemetry_refresher.start(lambda p: broadcast_system_alert(p, manager_broadcast_fn))
        logger.info("Telemetry refresher started at 10 Hz.")
    except Exception as exc:
        logger.warning(f"Telemetry refresher failed to start: {exc}")


async def execute_shutdown_sequence(vitals_router) -> None:
    """Stops all running background services cleanly."""
    global tunnel_proc
    try:
        telemetry_refresher.stop()
        logger.info("Telemetry refresher stopped.")
    except Exception:
        pass

    try:
        vitals_router.stop_daemon()
        logger.info("Vitals daemon stopped.")
    except Exception:
        pass

    try:
        from api.audio_daemon import audio_daemon_instance
        audio_daemon_instance.stop()
        logger.info("Audio isolation daemon stopped.")
    except Exception:
        pass

    if tunnel_proc:
        try:
            tunnel_proc.terminate()
            tunnel_proc.wait(timeout=2)
            logger.info("Cloudflare tunnel stopped.")
        except Exception:
            pass
        tunnel_proc = None
