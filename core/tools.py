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

    def open_website(self, site_name):
        site_name = site_name.lower().replace(" ", "")
        sites = {
            "youtube": "https://youtube.com",
            "google": "https://google.com",
            "github": "https://github.com",
            "chatgpt": "https://chatgpt.com"
        }
        url = sites.get(site_name, f"https://{site_name}.com")
        logger.info(f"[ACTION] Opening URL: {url}")
        webbrowser.open(url)
        return f"I have opened {site_name} for you, sir."

    def get_time(self):
        current_time = datetime.datetime.now().strftime("%I:%M %p")
        return f"The current time is {current_time}."

    def open_application(self, app_name):
        app_name_lower = app_name.lower().strip()
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
                os.system(f'start "" "{app_path}"')
                return f"Launching {app_name} now."
            except Exception as e:
                 return f"I encountered an error opening {app_name}."
        return f"I do not know the path for the application {app_name}."

    def read_clipboard(self):
        """Reads text from the system clipboard."""
        try:
            content = pyperclip.paste()
            if not content: return "The clipboard is empty, sir."
            return f"The clipboard contains: {content[:200]}..." # Return snippet
        except Exception as e:
            return f"I couldn't read the clipboard: {e}"

    def write_clipboard(self, text):
        """Copies text to the system clipboard."""
        try:
            pyperclip.copy(text)
            return "I have copied that to your clipboard, sir."
        except Exception as e:
            return f"Failed to copy to clipboard: {e}"

    def take_screenshot(self):
        """Captures a screenshot and saves it locally."""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            # Using ImageGrab for standard Windows compatibility
            snapshot = ImageGrab.grab()
            snapshot.save(filename)
            return f"Screenshot captured and saved as {filename}, sir."
        except Exception as e:
            return f"Failed to take screenshot: {e}"

    def type_text(self, text):
        """Types text at the current cursor position."""
        try:
            pyautogui.write(text, interval=0.01)
            return "Text has been typed, sir."
        except Exception as e:
            return f"Typing failed: {e}"
