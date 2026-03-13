import time
import asyncio

class WiFiDensePoseSensor:
    """
    WiFi-DensePose integration: Tracks body pose through walls using only WiFi signals.
    Provides presence awareness without cameras.
    """
    def __init__(self):
        self.user_present = False
        self.last_seen_time = time.time()
        self.session_active = False

    async def monitor_presence(self):
        """Background loop simulating WiFi CSI stream parsing for human presence."""
        print("[WiFi-DensePose] Tracking active - scanning CSI anomalies...")
        while True:
            await asyncio.sleep(10) # check every 10s
            # In actual implementation: process WiFi CSI packets
            # If presence detected: self.user_present = True
            
            # Pseudocode trigger:
            if not self.session_active and self.user_present:
                self._handle_arrival()
            elif self.session_active and not self.user_present:
                self._handle_departure()

    def _handle_arrival(self):
        print("[Presence] User arrived at desk. Auto-starting work session.")
        self.session_active = True
        absence_duration = time.time() - self.last_seen_time
        if absence_duration > 3600:
            hours = int(absence_duration // 3600)
            mins = int((absence_duration % 3600) // 60)
            print(f"[SPARK Voice] Welcome back — you were gone {hours} hours {mins} mins. Here's what you missed.")

    def _handle_departure(self):
        print("[Presence] User left desk. Saving state.")
        self.session_active = False
        self.last_seen_time = time.time()

presence_sensor = WiFiDensePoseSensor()
