import datetime
import os
import webbrowser


class SparkTools:
    def __init__(self):
        print("Initializing S.P.A.R.K. Tools...")

    def open_website(self, site_name):
        sites = {
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "github": "https://github.com",
            "chatgpt": "https://chatgpt.com",
        }
        url = sites.get(site_name.lower())
        if url:
            print(f"[ACTION] Opening {site_name}")
            webbrowser.open(url)
            return f"I have opened {site_name} for you, sir."
        return f"I do not have a registered URL for {site_name}."

    def get_time(self):
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        print(f"[ACTION] Checking time: {current_time}")
        return f"The current time is {current_time}."

    def open_application(self, app_name):
        # NOTE: These paths are standard Windows defaults.
        # You may need to update them if your apps are installed elsewhere.
        apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
            "code": "code",  # Assumes VS Code is in your PATH.
        }
        app_path = apps.get(app_name.lower())
        if app_path:
            try:
                print(f"[ACTION] Launching {app_name}")
                os.system(f'start "" "{app_path}"')
                return f"Launching {app_name} now."
            except Exception as e:
                return f"I encountered an error opening {app_name}: {e}"
        return f"I do not know the path for {app_name}."
