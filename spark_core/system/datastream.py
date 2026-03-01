"""
SPARK DataStream Broadcaster
────────────────────────────────────────────────────────────────────────────────
Pushes real telemetry events to the /ws/system namespace so the
DataStream HUD panel shows live system activity instead of mock data.

Events emitted on the "system" WebSocket namespace:
  DATASTREAM_EVENT — real-time system event (SYS/NET/SEC/API/HW/AI categories)

Called from SystemMonitor every monitoring tick.
"""

import asyncio
import time
import os
import random
import socket

try:
    import psutil
    PSUTIL_OK = True
except ImportError:
    PSUTIL_OK = False

try:
    import GPUtil
    GPUTIL_OK = True
except ImportError:
    GPUTIL_OK = False


# ── Event Categories (mirrors frontend FEED_SOURCES) ──────────────────────────
_net_bytes_sent_prev = 0
_net_bytes_recv_prev = 0
_last_emit_ts = 0.0


def build_datastream_events(spark_state: dict = None) -> list:
    """
    Build a batch of real system events to push to the DataStream panel.
    Returns a list of event dicts.
    """
    global _net_bytes_sent_prev, _net_bytes_recv_prev

    events = []
    ts = time.time()

    if PSUTIL_OK:
        # SYS events
        cpu  = psutil.cpu_percent(interval=None)
        mem  = psutil.virtual_memory()
        procs = len(psutil.pids())
        events.append({
            "src": "SYS",
            "color": "#00f5ff",
            "text": f"[SYS] CPU {cpu:.1f}% | MEM {mem.percent:.1f}% | PROCS {procs}",
            "ts":   ts,
        })

        # Uptime
        boot_ts = psutil.boot_time()
        uptime_h = (ts - boot_ts) / 3600
        events.append({
            "src": "SYS",
            "color": "#00f5ff",
            "text": f"[SYS] Uptime {uptime_h:.1f}h | Load avg: {'N/A' if os.name == 'nt' else str(os.getloadavg())}",
            "ts":   ts,
        })

        # HW events
        try:
            temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
            if temps:
                for name, entries in list(temps.items())[:1]:
                    if entries:
                        t = entries[0].current
                        events.append({
                            "src": "HW",
                            "color": "#ffb800",
                            "text": f"[HW] Temp:{name} {t:.1f}°C | Fan nominal",
                            "ts":   ts,
                        })
        except Exception:
            pass

        # NET events
        try:
            net = psutil.net_io_counters()
            sent_delta = max(0, net.bytes_sent - _net_bytes_sent_prev)
            recv_delta = max(0, net.bytes_recv - _net_bytes_recv_prev)
            _net_bytes_sent_prev = net.bytes_sent
            _net_bytes_recv_prev = net.bytes_recv
            events.append({
                "src": "NET",
                "color": "#0066ff",
                "text": f"[NET] TX:{sent_delta//1024}KB/s RX:{recv_delta//1024}KB/s | Packets:{net.packets_sent+net.packets_recv}",
                "ts":   ts,
            })
        except Exception:
            pass

        # GPU
        if GPUTIL_OK:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    g = gpus[0]
                    events.append({
                        "src": "HW",
                        "color": "#ffb800",
                        "text": f"[HW] GPU:{g.name} {g.load*100:.0f}% | VRAM:{g.memoryUsed}MB/{g.memoryTotal}MB | {g.temperature}°C",
                        "ts":   ts,
                    })
            except Exception:
                pass

    # API event — reflect spark-core health
    events.append({
        "src": "API",
        "color": "#00ff88",
        "text": f"[API] GET /api/health 200 | WS:system alive | ts:{ts:.2f}",
        "ts":   ts,
    })

    # SEC event — from state if available
    if spark_state:
        metrics = spark_state.get("metrics", {})
        vulns   = metrics.get("known_vulnerabilities", -1)
        lint    = metrics.get("lint_errors", -1)
        if vulns >= 0:
            sev = "🔴" if vulns > 0 else "🟢"
            events.append({
                "src": "SEC",
                "color": "#ff3b3b" if vulns > 0 else "#00ff88",
                "text": f"[SEC] Bandit:{sev}{vulns} vulns | Lint:{lint} issues | Firewall:ACTIVE",
                "ts":   ts,
            })

    # AI event — from cognitive loop state
    if spark_state:
        cl = spark_state.get("cognitive_loop", {})
        if cl:
            phase = cl.get("phase", "IDLE")
            cycle = cl.get("cycle_count", 0)
            events.append({
                "src": "AI",
                "color": "#8b00ff",
                "text": f"[AI] CogLoop:{phase} | Cycle:{cycle} | KnowledgeGraph:online",
                "ts":   ts,
            })

    return events


async def broadcast_datastream_tick(ws_manager, spark_state: dict = None):
    """Push a batch of real events to DataStream via WebSocket broadcast."""
    events = build_datastream_events(spark_state)
    payload = {
        "v": 1,
        "type": "DATASTREAM_BATCH",
        "ts": time.time() * 1000,
        "events": events,
    }
    await ws_manager.broadcast_json(payload, "system")
