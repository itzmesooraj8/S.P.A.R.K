import pyautogui
import os
from datetime import datetime

class ScreenAwareness:
    def __init__(self, screenshop_dir="./screenshots"):
        self.screenshot_dir = screenshop_dir
        if not os.path.exists(self.screenshot_dir):
            os.makedirs(self.screenshot_dir)
            print(f"[VISION] Created screenshot directory at {self.screenshot_dir}")

    def capture_screen(self):
        """
        Captures the current desktop screen and saves it as a PNG.
        Returns the file path of the captured image.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename)
            
            # Use pyautogui to capture the screen
            screenshot = pyautogui.screenshot()
            screenshot.save(filepath)
            
            print(f"[VISION] Screen captured and saved to: {filepath}")
            return os.path.abspath(filepath)
        except Exception as e:
            print(f"[VISION] Failed to capture screen: {e}")
            return None

# Singleton for system vision
screen_vision = ScreenAwareness()

if __name__ == "__main__":
    # Test capture
    path = screen_vision.capture_screen()
    if path:
        print(f"Test Success: {path}")
