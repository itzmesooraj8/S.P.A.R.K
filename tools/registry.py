import re
import threading
import queue
import time
import random
from duckduckgo_search import DDGS

class ToolRegistry:
    def __init__(self):
        self.tools = {
            "web_search": self.web_search,
            "system_scan": self.system_scan,
            "vision_scan": self.vision_scan,
            "kill_process": self.kill_process,
            "screenshot": self.screenshot,
            "network_scan": self.network_scan
        }
        # Regex to capture [EXECUTE: function_name("args")]
        # Handles optional spaces and quotes
        self.trigger_pattern = r"\[EXECUTE:\s*(\w+)\((.*)\)\]"

    def parse_and_execute(self, llm_output):
        """
        Parses the LLM output for tool triggers.
        Returns: (is_tool_triggered, result_string)
        """
        match = re.search(self.trigger_pattern, llm_output)
        if match:
            tool_name = match.group(1)
            args_str = match.group(2)
            
            # Clean arguments (remove quotes if simpler)
            # This is a basic parser. For cleaner args, we might need a better regex or ast.literal_eval
            args = args_str.strip('"').strip("'")
            
            if tool_name in self.tools:
                print(f"Tool Triggered: {tool_name} with args: {args}")
                return True, self._run_with_timeout(tool_name, args)
            else:
                return True, f"[SYSTEM_ERROR: Tool '{tool_name}' not found.]"
        
        return False, None

    def _run_with_timeout(self, tool_name, args, timeout=5):
        """Runs the tool in a separate thread with a timeout."""
        result_queue = queue.Queue()
        
        def target():
            try:
                res = self.tools[tool_name](args)
                result_queue.put(res)
            except Exception as e:
                result_queue.put(f"[SYSTEM_ERROR: {e}]")

        t = threading.Thread(target=target)
        t.start()
        t.join(timeout)
        
        if t.is_alive():
            # If still alive after timeout, we can't easily kill threads in Python
            # But we can ignore the result and return error
            return "[SYSTEM_ERROR: Tool execution timed out.]"
        
        if not result_queue.empty():
            return f"[SYSTEM_TOOL_OUTPUT: {result_queue.get()}]"
        return "[SYSTEM_ERROR: No output from tool.]"

    # --- Tool Definitions ---

    def web_search(self, query):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=3))
                if not results:
                    return "No results found."
                # Summarize top 3 results
                summary = ""
                for i, res in enumerate(results):
                    summary += f"{i+1}. {res['title']}: {res['body']}\n"
                return summary
        except Exception as e:
            return f"Search failed: {e}"

    def system_scan(self, _):
        # Placeholder for deeper scan
        import psutil
        return f"CPU: {psutil.cpu_percent()}%, RAM: {psutil.virtual_memory().percent}%"

    def vision_scan(self, _):
        # Tactical Vision: Now defaults to screen awareness but keeps camera fallback if needed
        return self.screenshot(_)

    def screenshot(self, _):
        from vision.screen import screen_vision
        from vision.describer import VisionDescriber
        
        try:
            save_path = screen_vision.capture_screen()
            if save_path:
                describer = VisionDescriber()
                return describer.describe(save_path)
            return "[VISION_ERROR: Screen capture failed.]"
        except Exception as e:
            return f"[VISION_ERROR: {e}]"

    def kill_process(self, target):
        import psutil
        try:
            if str(target).isdigit():
                pid = int(target)
                p = psutil.Process(pid)
                p.kill()
                return f"Terminated process PID: {pid}"
            else:
                count = 0
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'].lower() == target.lower():
                        proc.kill()
                        count += 1
                return f"Terminated {count} instances of {target}"
        except Exception as e:
            return f"Error killing process {target}: {e}"

    def network_scan(self, _):
        # Tactical Stub: Ready for nmap integration in Phase 3
        return "Network Scan Result: 192.168.1.1 (Gateway), 192.168.1.15 (Host), 192.168.1.42 (IoT Node)"
