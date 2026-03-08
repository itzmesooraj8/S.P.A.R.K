"""
SPARK System History Buffer
────────────────────────────────────────────────────────────────────────────────
Maintains a circular buffer of system metrics for the past ~10 minutes.
This allows the HUD analytics chart to pre-fill on reload instead of starting empty.

Data points captured:
  - CPU usage (%)
  - Memory usage (%)
  - GPU usage (%) if available
  - Network I/O (bytes/sec)
  - Timestamp (epoch ms)
"""

import asyncio
import time
from collections import deque
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import psutil

try:
    import GPUtil
    GPUTIL_OK = True
except ImportError:
    GPUTIL_OK = False


@dataclass
class SystemMetrics:
    """Single snapshot of system metrics at a point in time."""
    timestamp_ms: float  # epoch milliseconds
    cpu_percent: float   # 0-100
    memory_percent: float  # 0-100
    memory_available_gb: float
    gpu_percent: float   # 0-100 or -1 if unavailable
    net_sent_mbps: float  # megabits per second
    net_recv_mbps: float  # megabits per second


class SystemHistoryBuffer:
    """
    Circular buffer holding ~60 metrics snapshots (10 minutes @ 10s intervals).
    """
    
    MAX_SAMPLES = 60  # Store 60 samples
    
    def __init__(self):
        self.buffer: deque = deque(maxlen=self.MAX_SAMPLES)
        self._last_net_bytes_sent = 0
        self._last_net_bytes_recv = 0
        self._last_sample_time = time.time()
        
        # Pre-initialize network counters
        try:
            net = psutil.net_io_counters()
            self._last_net_bytes_sent = net.bytes_sent
            self._last_net_bytes_recv = net.bytes_recv
        except Exception:
            pass
    
    async def record_sample(self) -> SystemMetrics:
        """
        Capture current system metrics and add to circular buffer.
        Returns the recorded metrics dataclass.
        """
        try:
            ts_ms = time.time() * 1000
            
            # CPU usage
            cpu = psutil.cpu_percent(interval=None)
            
            # Memory
            mem = psutil.virtual_memory()
            mem_available_gb = mem.available / (1024 ** 3)
            
            # GPU (if available)
            gpu_percent = -1.0
            if GPUTIL_OK:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu_percent = gpus[0].load * 100
                except Exception:
                    pass
            
            # Network (bytes per second converted to Mbps)
            net_sent_mbps = 0.0
            net_recv_mbps = 0.0
            try:
                now = time.time()
                net = psutil.net_io_counters()
                elapsed = max(now - self._last_sample_time, 0.1)  # Avoid divide by zero
                
                bytes_sent_delta = max(0, net.bytes_sent - self._last_net_bytes_sent)
                bytes_recv_delta = max(0, net.bytes_recv - self._last_net_bytes_recv)
                
                # Convert to Mbps (bits per second / 1,000,000)
                net_sent_mbps = (bytes_sent_delta * 8) / (elapsed * 1_000_000)
                net_recv_mbps = (bytes_recv_delta * 8) / (elapsed * 1_000_000)
                
                self._last_net_bytes_sent = net.bytes_sent
                self._last_net_bytes_recv = net.bytes_recv
                self._last_sample_time = now
            except Exception:
                pass
            
            metrics = SystemMetrics(
                timestamp_ms=ts_ms,
                cpu_percent=cpu,
                memory_percent=mem.percent,
                memory_available_gb=mem_available_gb,
                gpu_percent=gpu_percent,
                net_sent_mbps=net_sent_mbps,
                net_recv_mbps=net_recv_mbps,
            )
            
            # Add to circular buffer
            self.buffer.append(metrics)
            
            return metrics
        except Exception as exc:
            print(f"❌ [SystemHistory] Failed to record sample: {exc}")
            # Return a zero-filled metrics object on error
            return SystemMetrics(
                timestamp_ms=time.time() * 1000,
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_available_gb=0.0,
                gpu_percent=-1.0,
                net_sent_mbps=0.0,
                net_recv_mbps=0.0,
            )
    
    def get_history(self) -> List[Dict[str, Any]]:
        """
        Return entire buffer as list of dicts (oldest to newest).
        Used to pre-fill charts on HUD load.
        """
        return [asdict(m) for m in self.buffer]
    
    def get_latest(self) -> Dict[str, Any]:
        """Return the most recent metrics snapshot."""
        if not self.buffer:
            return {}
        return asdict(self.buffer[-1])
    
    def clear(self):
        """Clear all history. Used for testing/debugging."""
        self.buffer.clear()


# Global singleton
history_buffer = SystemHistoryBuffer()

