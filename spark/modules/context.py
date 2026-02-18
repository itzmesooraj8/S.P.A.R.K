"""
S.P.A.R.K. Context Manager
--------------------------
This module provides real-time context about the user's environment.
It answers questions like:
- "What app is the user looking at?" (Active Window)
- "Is the system under load?" (CPU/RAM)
- "What time is it?" (Day/Night cycle)
"""

import datetime
import psutil
try:
    import pygetwindow as gw
except ImportError:
    gw = None

class ContextManager:
    def __init__(self):
        self.last_context = {}

    def get_active_window(self):
        """Returns the title of the currently active window."""
        if not gw:
            return "Unknown (pygetwindow not installed)"
        try:
            window = gw.getActiveWindow()
            if window:
                return window.title.strip()
            return "Unknown (No active window)"
        except Exception:
            return "Unknown (Error retrieving window)"

    def get_system_stats(self):
        """Returns a summary of CPU and RAM usage."""
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        return f"CPU: {cpu}%, RAM: {ram}%"

    def get_time_context(self):
        """Returns a human-readable time context."""
        now = datetime.datetime.now()
        hour = now.hour
        if 5 <= hour < 12:
            return "Morning"
        elif 12 <= hour < 17:
            return "Afternoon"
        elif 17 <= hour < 21:
            return "Evening"
        else:
            return "Night"

    def capture_context(self):
        """Captures a snapshot of the current environment."""
        context = {
            "active_window": self.get_active_window(),
            "system_stats": self.get_system_stats(),
            "time_of_day": self.get_time_context(),
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.last_context = context
        return context

# Singleton instance
context_manager = ContextManager()

if __name__ == "__main__":
    print("--- Context Manager Test ---")
    ctx = context_manager.capture_context()
    for k, v in ctx.items():
        print(f"{k}: {v}")
