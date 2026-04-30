import webbrowser
import os
import datetime
import logging
import pyperclip
import pyautogui
from PIL import ImageGrab

logger = logging.getLogger("SPARK_TOOLS")

class SparkTools:
    def __init__(self):
        logger.info("Initializing S.P.A.R.K. Multi-Tool Suite...")

    def open_website(self, site_arg):
        """OODA ACT: Robust URL normalization to prevent double-schemes/domains."""
        # Step 1: Detect placeholder hallucinations (meta-variables)
        placeholders = ["site_name", "url_here", "google_dot_com", "example_dot_com"]
        if site_arg.lower() in placeholders or " " in site_arg:
            logger.warning(f"Detected placeholder or malformed site_arg: {site_arg}")
            return "Sir, I detected a placeholder URL in my reasoning. Could you please specify which website you'd like to open?"

        # Step 2: Normalize the input
        site_arg = site_arg.lower().strip()
        
        # Step 3: Hardcoded mapping for speed
        sites = {
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "github": "https://github.com",
            "chatgpt": "https://chatgpt.com",
            "accuweather": "https://accuweather.com"
        }
        
        if site_arg in sites:
            target_url = sites[site_arg]
        else:
            # Step 4: Logic to handle partial or full URLs
            target_url = site_arg
            # Prepend https if no scheme is present
            if not target_url.startswith("http"):
                target_url = "https://" + target_url
            
            # Basic domain check - if no dot is present and it's not a known local host
            if "." not in target_url and "localhost" not in target_url:
                target_url += ".com"

        logger.info(f"[ACTION] Opening Normalized URL: {target_url}")
        webbrowser.open(target_url)
        return f"I have opened {target_url} for you, sir."

    def get_time(self):
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}."

    def open_application(self, app_name):
        app_name_lower = app_name.lower().strip()
        # Redirection for web services erroneously called as apps
        web_services = ["youtube", "google", "github", "facebook", "accuweather"]
        if any(service in app_name_lower for service in web_services):
            return self.open_website(app_name_lower)
            
        apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        }
        app_path = apps.get(app_name_lower)
        if app_path:
            try:
                os.system(f'start "" "{app_path}"')
                return f"Launching {app_name} now."
            except Exception as e:
                 return f"I encountered an error opening {app_name}."
        return f"I do not know the path for the application {app_name}."

    def read_clipboard(self):
        try:
            content = pyperclip.paste()
            if not content: return "The clipboard is empty, sir."
            return f"The clipboard contains: {content[:200]}..."
        except Exception as e:
            return f"I couldn't read the clipboard: {e}"

    def write_clipboard(self, text):
        try:
            pyperclip.copy(text)
            return "I have copied that to your clipboard, sir."
        except Exception as e:
            return f"Failed to copy to clipboard: {e}"

    def take_screenshot(self):
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            snapshot = ImageGrab.grab()
            snapshot.save(filename)
            return f"Screenshot captured as {filename}, sir."
        except Exception as e:
            return f"Failed to take screenshot: {e}"

    def type_text(self, text):
        try:
            pyautogui.write(text, interval=0.01)
            return "Text has been typed, sir."
        except Exception as e:
            return f"Typing failed: {e}"
