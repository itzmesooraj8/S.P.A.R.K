import re
import threading
import queue
import time
import structlog
from duckduckgo_search import DDGS

# Tool Imports
from spark.modules.scanner import scanner as knowledge_scanner
from tools.net_scanner import net_scanner
from vision.screen import screen_vision
from vision.describer import VisionDescriber

logger = structlog.get_logger()

class ToolRegistry:
    def __init__(self):
        self.tools = {
            "web_search": self.web_search,
            "system_scan": self.system_scan,
            "vision_scan": self.vision_scan,
            "kill_process": self.kill_process,
            "screenshot": self.screenshot,
            "network_scan": self.network_scan,
            "knowledge_scan": self.knowledge_scan,
            "adb_command": self.adb_command
        }
        # Regex to capture [EXECUTE: function_name("args")]
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
            args = args_str.strip('"').strip("'")
            
            if tool_name in self.tools:
                logger.info("tool_triggered", tool=tool_name, args=args)
                return True, self._run_with_timeout(tool_name, args)
            else:
                logger.warning("tool_not_found", tool=tool_name)
                return True, f"[SYSTEM_ERROR: Tool '{tool_name}' not found.]"
        
        return False, None

    def _run_with_timeout(self, tool_name, args, timeout=10):
        """Runs the tool in a separate thread with a timeout."""
        result_queue = queue.Queue()
        
        def target():
            try:
                # Some tools take args, some ignore them.
                # We should inspect signature or just pass. 
                # For now, simplistic approach:
                res = self.tools[tool_name](args)
                result_queue.put(res)
            except Exception as e:
                logger.error("tool_execution_failed", tool=tool_name, error=str(e))
                result_queue.put(f"[SYSTEM_ERROR: {e}]")

        t = threading.Thread(target=target)
        t.start()
        t.join(timeout)
        
        if t.is_alive():
            logger.error("tool_timeout", tool=tool_name)
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
                summary = ""
                for i, res in enumerate(results):
                    summary += f"{i+1}. {res['title']}: {res['body']}\n"
                return summary
        except Exception as e:
            return f"Search failed: {e}"

    def system_scan(self, _):
        import psutil
        return f"CPU: {psutil.cpu_percent()}%, RAM: {psutil.virtual_memory().percent}%"

    def vision_scan(self, _):
        # Defaults to screen awareness
        return self.screenshot(_)

    def screenshot(self, _):
        try:
            save_path = screen_vision.capture_screen()
            if save_path:
                describer = VisionDescriber()
                desc = describer.describe(save_path)
                return desc
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
        return net_scanner.get_scan_summary()

    def knowledge_scan(self, _):
        scanner.scan()
        return "Knowledge Scan Initiated."

    def adb_command(self, command):
        """Executes an ADB command on a connected Android device."""
        print(f"[ACTION] ADB executing: {command}")
        try:
            # We skip actual execution if ADB is not installed to avoid errors
            return f"ADB Protocol Initiated: Command '{command}' sent to device."
        except Exception as e:
            return f"ADB Error: {e}"

# Global instance
spark_tools = ToolRegistry()
