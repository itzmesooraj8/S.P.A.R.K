"""
S.P.A.R.K Embedded Electronics & Telemetry Interfacing Core
Includes asyncio serial packet parsers, dynamic power bus estimators,
PID stabilization controllers, and local OTA firmware flashing utilities.
"""

import asyncio
import json
import logging
import struct
import time
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("SPARK_TELEMETRY")

# Optional PySerial import
serial = None
try:
    import serial as s
    serial = s
except ImportError:
    logger.warning("pyserial not installed. Falling back to simulated serial stream.")

class EdgeTelemetryParser:
    """Asynchronously parses incoming UART/SPI/I2C binary data packets from edge microcontrollers."""
    
    def __init__(self, port: str = "COM3", baudrate: int = 115200, use_simulation: bool = False):
        self.port = port
        self.baudrate = baudrate
        self.use_simulation = use_simulation or (serial is None)
        self.system_status: Dict[str, Any] = {}
        self.running = False

    async def start_parsing(self, packet_callback: Optional[Any] = None) -> None:
        """Asynchronously reads and parses the binary serial stream."""
        self.running = True
        logger.info(f"Edge Telemetry: Starting packet parser on port: {self.port}")
        
        while self.running:
            if self.use_simulation:
                # Generate synthetic sensor data packet [Header(2B), Roll(4Bf), Pitch(4Bf), Current(4Bf), Voltage(4Bf), Checksum(1B)]
                await asyncio.sleep(0.1)
                sim_data = struct.pack("<2sffffB", b"ST", 1.25, -0.45, 2.1, 12.0, 0xAA)
                self._parse_packet_bytes(sim_data)
                if packet_callback:
                    packet_callback(self.system_status)
            else:
                try:
                    # Open serial port asynchronously in a threadpool to prevent blocking the event loop
                    ser = serial.Serial(self.port, self.baudrate, timeout=1.0)
                    while self.running:
                        # Non-blocking check
                        if ser.in_waiting >= 19:
                            data = ser.read(19)
                            self._parse_packet_bytes(data)
                            if packet_callback:
                                packet_callback(self.system_status)
                        await asyncio.sleep(0.01)
                    ser.close()
                except Exception as e:
                    logger.error(f"Serial communications error on {self.port}: {e}. Switching to simulation.")
                    self.use_simulation = True

    def _parse_packet_bytes(self, data: bytes) -> None:
        """Unpacks UART frames extracting telemetry values."""
        if len(data) < 19 or not data.startswith(b"ST"):
            return
            
        try:
            # Unpack bytes using struct
            header, roll, pitch, current, voltage, checksum = struct.unpack("<2sffffB", data)
            self.system_status = {
                "timestamp": time.time(),
                "imu_roll": float(roll),
                "imu_pitch": float(pitch),
                "motor_current": float(current),
                "motor_voltage": float(voltage),
                "load_power_w": float(current * voltage)
            }
        except struct.error as e:
            logger.debug(f"Failed unpacking serial packet frame: {e}")

class PowerBusSupervisor:
    """Monitors power redistribution factors and acts on voltage anomalies."""
    
    def __init__(self, critical_voltage_threshold: float = 10.5):
        self.threshold = critical_voltage_threshold
        
    def evaluate_bus_loads(self, telemetry_status: Dict[str, Any]) -> str:
        """Analyzes active electrical loads, triggering power profiles if anomalies occur."""
        voltage = telemetry_status.get("motor_voltage", 12.0)
        current = telemetry_status.get("motor_current", 0.0)
        power = current * voltage
        
        if voltage < self.threshold:
            logger.warning(f"POWER CRITICAL: Voltage dropout detected! Voltage={voltage:.2f}V < {self.threshold}V")
            return "emergency_low_power_profile"
        elif power > 40.0: # high load (e.g. > 40W)
            return "high_load_throttled_profile"
            
        return "nominal_power_profile"

class PIDBalanceFilter:
    """Stabilizes robotic equilibrium using IMU pitch/roll telemetry values."""
    
    def __init__(self, kp: float = 2.0, ki: float = 0.5, kd: float = 0.1):
        self.kp = kp
        self.ki = ki
        self.kd = kd
        
        self.integral = 0.0
        self.last_error = 0.0
        self.last_time = time.time()

    def compute_stabilization_output(self, current_angle: float, target_angle: float = 0.0) -> float:
        """Calculates Proportional-Integral-Derivative correction offsets."""
        now = time.time()
        dt = max(0.001, now - self.last_time)
        
        error = target_angle - current_angle
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        
        output = (self.kp * error) + (self.ki * self.integral) + (self.kd * derivative)
        
        self.last_error = error
        self.last_time = now
        return float(output)

class OTALoaderEngine:
    """Assembles binary image blocks and flashes remote targets via ESPOTA protocols."""
    
    def __init__(self, target_ip: str = "192.168.1.50"):
        self.target_ip = target_ip

    def compile_firmware_blob(self, config_params: Dict[str, Any]) -> bytes:
        """Builds mock binary payload representing embedded flash instruction code."""
        # Represents local compiler building a binary file
        header = b"ESPOTA_FIRMWARE_HEADER\x00\x01\x02"
        body = json.dumps(config_params).encode("utf-8")
        return header + body

    def flash_ota(self, binary_blob: bytes) -> Tuple[bool, str]:
        """Transmits code payloads to ESPOTA endpoints over local WiFi networks."""
        # Simple simulated TCP socket flash transfer
        logger.info(f"OTA Flasher: Connecting to remote ESP OTA target: {self.target_ip}:8266")
        time.sleep(0.2) # simulate socket handshake
        
        if not binary_blob.startswith(b"ESPOTA_FIRMWARE_HEADER"):
            return False, "OTA_FAILED: Invalid binary header format."
            
        logger.info(f"OTA Flasher: Transmitted {len(binary_blob)} bytes to remote device successfully.")
        return True, "OTA_SUCCESS: Firmware updated."
