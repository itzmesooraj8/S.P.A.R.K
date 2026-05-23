import webbrowser
import os
import datetime
import logging
try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    import pyautogui
except Exception:
    pyautogui = None

try:
    from PIL import ImageGrab
except ImportError:
    ImageGrab = None

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
        import re

        # Strict type check
        if not isinstance(app_name, str):
            app_name = str(app_name) if app_name is not None else ""

        app_name_clean = app_name.lower().strip()

        # Safeguard: Prevent treating conversational phrases as raw program names
        words = app_name_clean.split()
        invalid_keywords = {"create", "code", "run", "do", "make", "write", "find", "search", "website", "html", "file", "folder"}
        if len(words) > 3 or any(w in invalid_keywords for w in words):
            logger.warning(f"Aborted opening application due to conversational search guard: {app_name}")
            return f"LAUNCH_FAILED: Refusing to search for application with conversational phrase '{app_name}'."

        # Cleanup space-separated names of common web services and speech errors
        speech_replacements = {
            "you tube": "youtube",
            "git hub": "github",
            "face book": "facebook",
            "accu weather": "accuweather",
            "google maps": "maps",
        }
        for err, rep in speech_replacements.items():
            if err in app_name_clean:
                app_name_clean = app_name_clean.replace(err, rep)

        # Check if structurally a URL
        is_url = False
        if app_name_clean.startswith(("http://", "https://", "www.")):
            is_url = True
        elif re.search(r"\.[a-zA-Z]{2,6}(/.*)?$", app_name_clean):
            is_url = True

        if is_url:
            return self.open_website(app_name_clean)

        # Redirection for web services erroneously called as apps
        web_services = ["youtube", "google", "github", "facebook", "accuweather"]
        if any(service in app_name_clean for service in web_services):
            return self.open_website(app_name_clean)
            
        apps = {
            "notepad": "notepad.exe",
            "calculator": "calc.exe",
            "chrome": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        }
        app_path = apps.get(app_name_clean)
        if app_path:
            try:
                import subprocess
                subprocess.Popen([app_path])
                return f"Launching {app_name} now."
            except Exception as e:
                 return f"I encountered an error opening {app_name}."
        return f"I do not know the path for the application {app_name}."


    def read_clipboard(self):
        if pyperclip is None:
            return "Clipboard operations are not supported on this platform."
        try:
            content = pyperclip.paste()
            if not content: return "The clipboard is empty, sir."
            return f"The clipboard contains: {content[:200]}..."
        except Exception as e:
            return f"I couldn't read the clipboard: {e}"

    def write_clipboard(self, text):
        if pyperclip is None:
            return "Clipboard operations are not supported on this platform."
        try:
            pyperclip.copy(text)
            return "I have copied that to your clipboard, sir."
        except Exception as e:
            return f"Failed to copy to clipboard: {e}"

    def take_screenshot(self):
        if ImageGrab is None:
            return "Screenshot capture is not supported on this platform.", None
        import tempfile
        try:
            # Security Fix: Use a secure named temporary file instead of predictable static name
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png", prefix="spark_snap_")
            temp_file.close()
            
            snapshot = ImageGrab.grab()
            snapshot.save(temp_file.name)
            return f"Screenshot securely captured, sir.", temp_file.name
        except Exception as e:
            return f"Failed to take screenshot: {e}", None

    def type_text(self, text):
        if pyautogui is None:
            return "Keyboard typing simulation is not supported on this platform."
        try:
            import win32gui
            # Security Fix: Active Window Check before typing blindly
            active_window = win32gui.GetWindowText(win32gui.GetForegroundWindow()).lower()
            blacklist = ["cmd", "command prompt", "powershell", "terminal", "password", "bank", "login"]
            
            if any(bad_word in active_window for bad_word in blacklist):
                logger.warning(f"Aborted typing due to sensitive window focus: {active_window}")
                return "Security override: Refusing to type into a potentially sensitive window."
                
            pyautogui.write(text, interval=0.01)
            return "Text has been typed, sir."
        except Exception as e:
            return f"Typing failed: {e}"
