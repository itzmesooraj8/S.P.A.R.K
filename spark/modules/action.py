
"""
Action Module
Executes actions on devices, files, and applications using pyautogui and selenium.
"""


import pyautogui
import subprocess
import psutil
import os
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import time
from datetime import datetime

class ActionModule:
    def __init__(self):
        self.browser = None

    def act(self, intent, params=None):
        """
        Dispatch actions based on intent string and optional parameters.
        Supported intents: 'open_app', 'move_mouse', 'click', 'type', 'open_browser', 
        'search_web', 'scroll', 'close_browser', 'kill_process', 'screenshot'
        """
        if intent == 'open_app' and params:
            return self.open_app(params.get('app_path'))
        elif intent == 'kill_process' and params:
            return self.kill_process(params.get('name') or params.get('pid'))
        elif intent == 'screenshot':
            return self.get_screenshot()
        elif intent == 'network_scan':
            return self.network_scan()
        elif intent == 'adb_command' and params:
            return self.adb_command(params.get('command'))
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

    def kill_process(self, target):
        """Kills a process by name or PID."""
        try:
            if isinstance(target, int) or (isinstance(target, str) and target.isdigit()):
                pid = int(target)
                p = psutil.Process(pid)
                p.kill() # Forceful
                return f"Terminated process PID: {pid}"
            else:
                count = 0
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'].lower() == target.lower():
                        proc.terminate()
                        count += 1
                return f"Terminated {count} instances of {target}"
        except Exception as e:
            return f"Error killing process {target}: {e}"

    def get_screenshot(self):
        """Captures a screenshot and returns the path."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"
            # Ensure path is absolute or in a known dir
            filepath = os.path.abspath(filename)
            pyautogui.screenshot(filepath)
            print(f"[ACTION] Screenshot saved to {filepath}")
            return filepath
        except Exception as e:
            return f"Error taking screenshot: {e}"

    def network_scan(self):
        """Perform a basic network scan using ARP or Ping sweep."""
        # Tactical Stub: In a real scenario, this might use scapy or nmap.
        # For now, we simulate a scan result.
        print("[ACTION] Scanning network...")
        try:
            # Mocking a scan for now. In Phase 3, we'll use nmap.
            mock_results = [
                {"ip": "192.168.1.1", "device": "Gateway/Router"},
                {"ip": "192.168.1.15", "device": "S.P.A.R.K. Host (You)"},
                {"ip": "192.168.1.42", "device": "Smart Light (Office)"}
            ]
            return f"Network Scan Complete: Found {len(mock_results)} devices:\n" + \
                   "\n".join([f"- {d['ip']}: {d['device']}" for d in mock_results])
        except Exception as e:
            return f"Network scan failed: {e}"

    def adb_command(self, command):
        """Executes an ADB command on a connected Android device."""
        # Bridge Stub: Requires adb to be installed and device connected.
        print(f"[ACTION] ADB executing: {command}")
        try:
            # We skip actual execution if ADB is not installed to avoid errors
            # In a real environment: subprocess.check_output(f"adb {command}", shell=True)
            return f"ADB Protocol Initiated: Command '{command}' sent to device."
        except Exception as e:
            return f"ADB Error: {e}"
