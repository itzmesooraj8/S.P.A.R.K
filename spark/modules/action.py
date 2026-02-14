
"""
Action Module
Executes actions on devices, files, and applications using pyautogui and selenium.
"""


import pyautogui
import subprocess
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time

class ActionModule:
    def __init__(self):
        self.browser = None

    def act(self, intent, params=None):
        """
        Dispatch actions based on intent string and optional parameters.
        Supported intents: 'open_app', 'move_mouse', 'click', 'type', 'open_browser', 'search_web', 'scroll', 'close_browser'
        """
        if intent == 'open_app' and params:
            return self.open_app(params.get('app_path'))
        elif intent == 'move_mouse' and params:
            return self.move_mouse(params.get('x'), params.get('y'))
        elif intent == 'click':
            return self.click()
        elif intent == 'type' and params:
            return self.type_text(params.get('text'))
        elif intent == 'open_browser':
            return self.open_browser()
        elif intent == 'search_web' and params:
            return self.search_web(params.get('query'))
        elif intent == 'scroll' and params:
            return self.scroll(params.get('amount'))
        elif intent == 'close_browser':
            return self.close_browser()
        else:
            print(f"[ACTION] Unknown or missing intent: {intent}")

    def open_app(self, app_path):
        try:
            subprocess.Popen(app_path)
            print(f"[ACTION] Opened app: {app_path}")
        except Exception as e:
            print(f"[ACTION] Failed to open app: {e}")

    def move_mouse(self, x, y):
        pyautogui.moveTo(x, y)
        print(f"[ACTION] Moved mouse to ({x}, {y})")

    def click(self):
        pyautogui.click()
        print("[ACTION] Mouse click")

    def type_text(self, text):
        pyautogui.write(text)
        print(f"[ACTION] Typed text: {text}")

    def open_browser(self):
        if self.browser is None:
            self.browser = webdriver.Chrome()
            print("[ACTION] Opened Chrome browser")
        else:
            print("[ACTION] Browser already open")

    def search_web(self, query):
        if self.browser is None:
            self.open_browser()
        self.browser.get("https://www.google.com")
        time.sleep(1)
        box = self.browser.find_element("name", "q")
        box.send_keys(query)
        box.send_keys(Keys.RETURN)
        print(f"[ACTION] Searched web for: {query}")

    def scroll(self, amount):
        pyautogui.scroll(amount)
        print(f"[ACTION] Scrolled by {amount}")

    def close_browser(self):
        if self.browser:
            self.browser.quit()
            self.browser = None
            print("[ACTION] Closed browser")
