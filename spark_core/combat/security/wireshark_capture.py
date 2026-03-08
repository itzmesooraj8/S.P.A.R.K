"""
Live Packet Capture via pyshark (Wireshark/tshark backend)
===========================================================
Streams packet summaries to the "combat" WebSocket namespace so the
CombatDock and SIGINT panel can display a live feed.

Requires:  pip install pyshark   +   Wireshark / tshark installed on OS.
Degrades gracefully: if pyshark is absent, returns mock packets.
"""
import asyncio
import logging
import uuid
from typing import Dict, Optional, AsyncIterator

log = logging.getLogger(__name__)

try:
    import pyshark  # type: ignore
    _PYSHARK_OK = True
except ImportError:
    _PYSHARK_OK = False
    log.warning("pyshark not installed — packet capture will use mock mode")

# In-memory registry of active captures: { job_id: asyncio.Task }
_active_captures: Dict[str, asyncio.Task] = {}


async def _capture_loop(
    interface: str,
    job_id: str,
    bpf_filter: str,
    max_packets: int,
) -> None:
    """Background task: capture packets and broadcast via WS."""
    try:
        from spark_core.ws.manager import ws_manager

        if _PYSHARK_OK:
            capture = pyshark.LiveCapture(
                interface=interface,
                bpf_filter=bpf_filter or None,
                use_json=True,
                include_raw=False,
            )
            count = 0
            async for pkt in capture.packets_from_tshark():
                if count >= max_packets:
                    break
                summary = {
                    "type": "PACKET",
                    "job_id": job_id,
                    "src": getattr(pkt, "ip", {}).src if hasattr(pkt, "ip") else "?",
                    "dst": getattr(pkt, "ip", {}).dst if hasattr(pkt, "ip") else "?",
                    "proto": pkt.highest_layer,
                    "length": int(pkt.length),
                    "info": str(pkt),
                }
                await ws_manager.broadcast("combat", summary)
                count += 1
        else:
            # Mock mode — send fake packets at 2/s
            import random, json
            hosts = ["10.0.0.1", "192.168.1.1", "8.8.8.8", "1.1.1.1"]
            protos = ["TCP", "UDP", "DNS", "HTTP", "TLS"]
            for i in range(min(max_packets, 200)):
                await asyncio.sleep(0.5)
                pkt = {
                    "type": "PACKET",
                    "job_id": job_id,
                    "src": random.choice(hosts),
                    "dst": random.choice(hosts),
                    "proto": random.choice(protos),
                    "length": random.randint(64, 1500),
                    "info": f"Mock packet #{i}",
                }
                await ws_manager.broadcast("combat", pkt)
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        log.error("capture_loop error: %s", exc)
    finally:
        _active_captures.pop(job_id, None)
        log.info("Capture job %s ended", job_id)


async def start_capture(
    interface: str = "eth0",
    bpf_filter: str = "",
    max_packets: int = 500,
) -> str:
    """Start a background capture job. Returns job_id."""
    job_id = str(uuid.uuid4())[:8]
    task = asyncio.create_task(
        _capture_loop(interface, job_id, bpf_filter, max_packets),
        name=f"capture_{job_id}",
    )
    _active_captures[job_id] = task
    log.info("Capture job %s started on %s (filter=%r)", job_id, interface, bpf_filter)
    return job_id


def stop_capture(job_id: str) -> bool:
    """Cancel an active capture job. Returns True if it was found."""
    task = _active_captures.pop(job_id, None)
    if task:
        task.cancel()
        return True
    return False


def list_captures() -> list:
    return [{"job_id": jid, "status": "running"} for jid in _active_captures]
