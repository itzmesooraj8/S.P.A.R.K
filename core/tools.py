import datetime
import os
import subprocess
import webbrowser

import psutil


class SparkTools:
    def __init__(self):
        print("Initializing S.P.A.R.K. Tools...")

    def open_browser(self, target):
        print(f"[ACTION] Opening {target}")
        webbrowser.open(target)
        return f"Opening {target}."

    def open_website(self, site_name):
        sites = {
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "github": "https://github.com",
            "chatgpt": "https://chatgpt.com",
        }
        url = sites.get(site_name.lower())
        if url:
            return self.open_browser(url)
        return f"I do not have a registered URL for {site_name}."

    def get_time(self):
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        print(f"[ACTION] Checking time: {current_time}")
        return f"The current time is {current_time}."

    def check_battery(self):
        battery = psutil.sensors_battery()
        if battery is None:
            return "I could not detect a battery on this system."
        plugged = "plugged in" if battery.power_plugged else "running on battery"
        return f"Battery is at {battery.percent:.0f} percent and is currently {plugged}."

    def open_application(self, app_name):
        apps = {
            "notepad": ["notepad.exe"],
            "calculator": ["calc.exe"],
            "chrome": ["C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"],
            "code": ["code"],
        }
        command = apps.get(app_name.lower())
        if command:
            try:
                print(f"[ACTION] Launching {app_name}")
                subprocess.Popen(command)
                return f"Launching {app_name} now."
            except Exception as exc:
                return f"I encountered an error opening {app_name}: {exc}"
        return f"I do not know the path for {app_name}."

    def shutdown_pc(self):
        print("[ACTION] Shutting down the PC")
        os.system("shutdown /s /t 0")
        return "Shutting down now."
