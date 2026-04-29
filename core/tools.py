import webbrowser
import os
import datetime
import logging

logger = logging.getLogger("SPARK_TOOLS")

class SparkTools:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Tools...")

    def open_website(self, site_name):
        # Clean up the name (e.g., "youtube" instead of "YouTube ")
        site_name = site_name.lower().replace(" ", "")
        sites = {
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "github": "https://github.com",
            "chatgpt": "https://chatgpt.com"
        }
        # Smart Fallback: If it's not in the dictionary, guess the .com address
        url = sites.get(site_name, f"https://{site_name}.com")
        
        logger.info(f"[ACTION] Opening URL: {url}")
        webbrowser.open(url)
        return f"I have opened {site_name} for you, sir."

    def get_time(self):
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}."

    def open_application(self, app_name):
        app_name_lower = app_name.lower().strip()
        
        # SMART FALLBACK: If it tries to open a website as an app, redirect it to the browser
        if app_name_lower in ["youtube", "google", "github", "facebook"]:
            return self.open_website(app_name_lower)
            
        apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        }
        app_path = apps.get(app_name_lower)
        if app_path:
            try:
                # Windows-specific execution
                os.startfile(app_path) if "://" not in app_path and not app_path.endswith(".exe") else os.system(f'start "" "{app_path}"')
                return f"Launching {app_name} now."
            except Exception as e:
                 return f"I encountered an error opening {app_name}."
        return f"I do not know the path for the application {app_name}."
