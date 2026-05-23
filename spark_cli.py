"""SPARK interactive CLI with premium holographic interface, themes, telemetry, typewriter streaming, and local slash commands."""

from __future__ import annotations

import argparse
import sys
import os
import time
import requests
import psutil
import threading
from pathlib import Path
from types import ModuleType
from typing import Any

# Ensure the `spark` package directory is importable in local mode
package_dir = Path(__file__).resolve().parent / "spark"
pkg = ModuleType("spark")
pkg.__path__ = [str(package_dir)]
sys.modules.setdefault("spark", pkg)

try:
    from spark.core import SparkCore, load_config
except ImportError:
    # SparkCore imports might fail on remote clients without full dependencies
    SparkCore = None
    def load_config(): return {}


# --- THEME STYLING CONFIGURATION ---
THEMES = {
    "cyberpunk": {
        "primary": "\033[38;5;51m",     # Neon Cyan
        "secondary": "\033[38;5;165m", # Hot Pink / Electric Magenta
        "success": "\033[38;5;82m",    # Neon Green
        "warning": "\033[38;5;214m",   # Amber / Orange
        "danger": "\033[38;5;196m",    # Hot Red
        "muted": "\033[38;5;244m",     # Cool Grey
        "reset": "\033[0m",
        "bg_block": "\033[48;5;235m",  # Dark grey bg
        "text_block": "\033[38;5;253m",# Soft white text
    },
    "matrix": {
        "primary": "\033[38;5;46m",     # Bright Green
        "secondary": "\033[38;5;34m",   # Dark Green
        "success": "\033[38;5;82m",     # Green
        "warning": "\033[38;5;190m",    # Yellow-Green
        "danger": "\033[38;5;160m",     # Crimson
        "muted": "\033[38;5;240m",     # Dark grey
        "reset": "\033[0m",
        "bg_block": "\033[48;5;232m",
        "text_block": "\033[38;5;120m",
    },
    "amber": {
        "primary": "\033[38;5;214m",     # Warm Amber
        "secondary": "\033[38;5;130m",   # Dark Amber / Brownish
        "success": "\033[38;5;208m",     # Orange-Amber
        "warning": "\033[38;5;220m",     # Bright Yellow
        "danger": "\033[38;5;196m",      # Red
        "muted": "\033[38;5;136m",      # Dull Amber
        "reset": "\033[0m",
        "bg_block": "\033[48;5;234m",
        "text_block": "\033[38;5;223m",
    },
    "deepspace": {
        "primary": "\033[38;5;99m",      # Deep Purple
        "secondary": "\033[38;5;33m",    # Electric Blue
        "success": "\033[38;5;48m",      # Spring Green
        "warning": "\033[38;5;214m",     # Gold
        "danger": "\033[38;5;203m",      # Coral Red
        "muted": "\033[38;5;60m",       # Slate Blue
        "reset": "\033[0m",
        "bg_block": "\033[48;5;233m",
        "text_block": "\033[38;5;189m",
    }
}


# --- HELPER FUNCTIONS ---
def get_progress_bar(percent: float, length: int = 10) -> str:
    filled = int(percent / 100 * length)
    empty = length - filled
    return "■" * filled + "□" * empty


def get_uptime_string(secs: float) -> str:
    h = int(secs // 3600)
    m = int((secs % 3600) // 60)
    s = int(secs % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def enable_ansi_escapes_on_windows() -> None:
    if sys.platform == "win32":
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            # Set console mode to support Virtual Terminal Processing (ENABLE_VIRTUAL_TERMINAL_PROCESSING = 4)
            # STD_OUTPUT_HANDLE = -11
            handle = kernel32.GetStdHandle(-11)
            mode = ctypes.c_ulong()
            if kernel32.GetConsoleMode(handle, ctypes.byref(mode)):
                kernel32.SetConsoleMode(handle, mode.value | 4)
        except Exception:
            pass


def format_and_print_response(text: str, theme: dict, speed: float = 0.012) -> None:
    """Typewriter markdown parser that formats headers, code blocks, bullet points, and inline styling."""
    lines = text.split("\n")
    in_code_block = False
    code_block_lines = []
    code_lang = ""
    
    sys.stdout.write(f"\n{theme['secondary']}{'━'*72}\n")
    sys.stdout.write(f"❖ S.P.A.R.K. RESPONSE LINK ESTABLISHED\n")
    sys.stdout.write(f"{theme['secondary']}{'━'*72}{theme['reset']}\n")
    
    current_speed = speed
    line_idx = 0
    
    try:
        while line_idx < len(lines):
            line = lines[line_idx]
            
            # Check code block boundary
            if line.strip().startswith("```"):
                if not in_code_block:
                    in_code_block = True
                    code_lang = line.strip().replace("```", "").strip()
                    border = f"┌─── [ {code_lang or 'CODE'} ] ───────────────────────────────────────────"
                    sys.stdout.write(f"\n{theme['primary']}{border}{theme['reset']}\n")
                    code_block_lines = []
                else:
                    in_code_block = False
                    for idx, cl in enumerate(code_block_lines):
                        formatted_line = f"│ {theme['muted']}{idx+1:02d} {theme['text_block']}{cl:<68}"
                        if current_speed > 0:
                            for char in formatted_line:
                                sys.stdout.write(char)
                                sys.stdout.flush()
                                time.sleep(current_speed * 0.3)
                            sys.stdout.write("\n")
                        else:
                            print(formatted_line)
                    
                    border_end = f"└──────────────────────────────────────────────────────────────────"
                    sys.stdout.write(f"{theme['primary']}{border_end}{theme['reset']}\n\n")
                line_idx += 1
                continue
                
            if in_code_block:
                code_block_lines.append(line)
                line_idx += 1
                continue
                
            # Headers
            if line.startswith("#"):
                hashes = len(line) - len(line.lstrip('#'))
                header_text = line.lstrip('#').strip()
                formatted = f"\n{theme['primary']}{'❖ ' * hashes}{header_text}{theme['reset']}\n"
                if current_speed > 0:
                    for char in formatted:
                        sys.stdout.write(char)
                        sys.stdout.flush()
                        time.sleep(current_speed)
                else:
                    print(formatted)
                line_idx += 1
                continue
                
            # List Items
            clean_line = line.strip()
            if clean_line.startswith(("- ", "* ", "+ ")):
                indent = "  " * (len(line) - len(line.lstrip()))
                bullet = f"{theme['success']}❯{theme['reset']}"
                item_text = clean_line[2:]
                formatted = f"{indent}{bullet} {item_text}\n"
                if current_speed > 0:
                    for char in formatted:
                        sys.stdout.write(char)
                        sys.stdout.flush()
                        time.sleep(current_speed)
                else:
                    print(formatted)
                line_idx += 1
                continue
                
            # Inline bold and code styling
            # Bold parser
            parts = line.split("**")
            if len(parts) > 1:
                new_line = ""
                for idx, part in enumerate(parts):
                    if idx % 2 == 1:
                        new_line += f"\033[1m{theme['secondary']}{part}\033[0m"
                    else:
                        new_line += part
                line = new_line
                
            # Inline code parser
            parts_code = line.split("`")
            if len(parts_code) > 1:
                new_line = ""
                for idx, part in enumerate(parts_code):
                    if idx % 2 == 1:
                        new_line += f"{theme['primary']}{part}{theme['reset']}"
                    else:
                        new_line += part
                line = new_line
                
            # Standard Text line
            formatted_line = line + "\n"
            if current_speed > 0:
                for char in formatted_line:
                    sys.stdout.write(char)
                    sys.stdout.flush()
                    time.sleep(current_speed)
            else:
                sys.stdout.write(formatted_line)
                sys.stdout.flush()
                
            line_idx += 1
            
    except KeyboardInterrupt:
        # Skip typewriter styling instantly
        current_speed = 0.0
        if in_code_block:
            for idx, cl in enumerate(code_block_lines):
                print(f"│ {theme['muted']}{idx+1:02d} {theme['text_block']}{cl:<68}")
            print(f"{theme['primary']}└──────────────────────────────────────────────────────────────────{theme['reset']}\n")
            in_code_block = False
            
        while line_idx < len(lines):
            line = lines[line_idx]
            if line.strip().startswith("```"):
                line_idx += 1
                continue
            
            # Format bold/code inline
            parts = line.split("**")
            if len(parts) > 1:
                new_line = ""
                for idx, part in enumerate(parts):
                    if idx % 2 == 1:
                        new_line += f"\033[1m{theme['secondary']}{part}\033[0m"
                    else:
                        new_line += part
                line = new_line
            parts_code = line.split("`")
            if len(parts_code) > 1:
                new_line = ""
                for idx, part in enumerate(parts_code):
                    if idx % 2 == 1:
                        new_line += f"{theme['primary']}{part}{theme['reset']}"
                    else:
                        new_line += part
                line = new_line
                
            print(line)
            line_idx += 1
            
    sys.stdout.write(f"{theme['secondary']}{'━'*72}{theme['reset']}\n")


class Spinner:
    """Futuristic loading spinner for query execution."""
    def __init__(self, theme: dict, message: str = "SPARK thinking"):
        self.message = message
        self.color = theme["primary"]
        self.reset = theme["reset"]
        self.spin_chars = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self._running = False
        self._thread = None

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        idx = 0
        messages = [
            "COLLATING COGNITIVE VECTORS",
            "ROUTING THOUGHT GRID",
            "CONSULTING DEEP MEMORY",
            "SYNTHESIZING SYSTEM STATE",
            "DECRYPTING RESPONSE PATH"
        ]
        msg_idx = 0
        last_msg_change = time.time()
        
        while self._running:
            if time.time() - last_msg_change > 1.2:
                msg_idx = (msg_idx + 1) % len(messages)
                sys.stdout.write("\r" + " " * 80)
                last_msg_change = time.time()
            
            sys.stdout.write(f"\r{self.color}{self.spin_chars[idx]} {messages[msg_idx]}...{self.reset}")
            sys.stdout.flush()
            idx = (idx + 1) % len(self.spin_chars)
            time.sleep(0.08)

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()


class SparkCLI:
    def __init__(self, remote_url: str | None = None, token: str | None = None):
        self.remote_url = remote_url.rstrip("/") if remote_url else None
        self.token = token or os.getenv("SPARK_ACCESS_TOKEN", "").strip()
        self.core = None
        self.session_count = 0
        self.theme_name = "cyberpunk"
        self.theme = THEMES[self.theme_name]
        self.typewriter_speed = 0.012
        self.start_time = time.time()
        self.ping_time = "N/A"

        enable_ansi_escapes_on_windows()

        if not self.remote_url:
            # Local mode
            if SparkCore is None:
                raise RuntimeError("Local dependencies missing. Please run with --remote <url>.")
            self.config = load_config()
            self.core = SparkCore(self.config)
            self._start_ollama_keepalive()
            try:
                from core.local_brain_chain import warmup_chain
                threading.Thread(target=warmup_chain, daemon=True, name="spark-warmup").start()
            except Exception:
                pass
        else:
            self._update_remote_ping()

    def _start_ollama_keepalive(self) -> None:
        import subprocess
        def _ensure_ollama() -> None:
            try:
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
            except Exception:
                pass

        threading.Thread(target=_ensure_ollama, daemon=True).start()

    def _update_remote_ping(self) -> None:
        if not self.remote_url:
            self.ping_time = "LOCAL"
            return
        
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        start = time.time()
        try:
            resp = requests.get(f"{self.remote_url}/ping", headers=headers, timeout=3)
            if resp.status_code == 200:
                elapsed = (time.time() - start) * 1000
                self.ping_time = f"{int(elapsed)} ms"
            else:
                self.ping_time = f"ERR {resp.status_code}"
        except Exception:
            self.ping_time = "TIMEOUT"

    def _print_hologram_header(self):
        primary = self.theme["primary"]
        secondary = self.theme["secondary"]
        success = self.theme["success"]
        reset = self.theme["reset"]
        
        # Display Futuristic Logo
        logo = f"""
{primary}  ██████╗██████╗  █████╗ ██████╗ ██╗  ██╗{secondary}  v3.0
{primary} ██╔════╝██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝{secondary}  [ Sovereign Personal AI ]
{primary} ╚█████╗ ██████╔╝███████║██████╔╝█████╔╝ {secondary}  [ Reasoning Kernel ]
{primary}  ╚═══██╗██╔═══╝ ██╔══██║██╔══██╗██╔═██╗ {reset}
{primary} ██████╔╝██║     ██║  ██║██║  ██║██║  ██╗{reset}
{primary} ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝{reset}
"""
        print(logo)
        
        try:
            cpu_pct = psutil.cpu_percent()
            ram_pct = psutil.virtual_memory().percent
        except Exception:
            cpu_pct = 0.0
            ram_pct = 0.0
            
        cpu_bar = get_progress_bar(cpu_pct, 10)
        ram_bar = get_progress_bar(ram_pct, 10)
        
        uptime = get_uptime_string(time.time() - self.start_time)
        systime = time.strftime("%Y-%m-%d %H:%M:%S")
        
        if self.remote_url:
            mode_text = f"REMOTE CLIENT -> {self.remote_url}"
            link_status = f"{success}SECURE LINK STABLE{reset}"
        else:
            mode_text = "LOCAL DIRECT ACCESS"
            link_status = f"{success}LOCAL ENGINE RUNNING{reset}"

        print(f"{primary}┌────────────────────────────────────────────────────────────────────────┐")
        print(f"│  S.P.A.R.K. Interactive Terminal [Holographic Interface]               │")
        print(f"├────────────────────────────────────────────────────────────────────────┤")
        print(f"│  {secondary}Mode{reset}    : {mode_text:<51} │")
        print(f"│  {secondary}Link{reset}    : {link_status:<62} │")
        print(f"│  {secondary}Latency{reset} : {self.ping_time:<51} │")
        print(f"├────────────────────────────────────────────────────────────────────────┤")
        print(f"│  {secondary}TELEMETRY{reset}:                                                            │")
        print(f"│  CPU Load: [{cpu_bar}] {cpu_pct:>4.1f}%     | RAM Usage: [{ram_bar}] {ram_pct:>4.1f}%           │")
        print(f"│  Uptime  : {uptime:<14}     | System Time: {systime:<20} │")
        print(f"└────────────────────────────────────────────────────────────────────────┘{reset}")
        print()

    def print_help(self) -> None:
        primary = self.theme["primary"]
        secondary = self.theme["secondary"]
        reset = self.theme["reset"]
        
        print(f"\n{primary}┌─── [ S.P.A.R.K. DIRECTIVE DIRECTORY ] ──────────────────────────────────┐")
        print(f"│ {secondary}Command{reset}         │ {secondary}Description{reset}                                              │")
        print(f"├─────────────────┼──────────────────────────────────────────────────────┤")
        print(f"│ /help           │ Displays this directive glossary.                    │")
        print(f"│ /clear          │ Flushes the console buffer and redraws terminal HUD. │")
        print(f"│ /ping           │ Calculates the signal roundtrip time.                │")
        print(f"│ /sys            │ Displays local/remote system hardware diagnostics.   │")
        print(f"│ /memory         │ Returns facts and associations in cognitive memory.   │")
        print(f"│ /theme [name]   │ Hot-swaps the styling theme interface.               │")
        print(f"│ /toggle-speed   │ Cycles typewriter streaming speed (Normal/Fast/None).│")
        print(f"│ /exit           │ Terminating the interactive connection.              │")
        print(f"{primary}└─────────────────┴──────────────────────────────────────────────────────┘{reset}\n")

    def print_system_info(self) -> None:
        primary = self.theme["primary"]
        secondary = self.theme["secondary"]
        reset = self.theme["reset"]
        
        print(f"\n{primary}┌─── [ SYSTEM INFRASTRUCTURE DIAGNOSTICS ] ────────────────────────────────┐")
        
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            cpu_cores = psutil.cpu_count(logical=True)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            cpu_info = f"{cpu_percent}% ({cpu_cores} Cores)"
            ram_info = f"{ram.percent}% of {ram.total / (1024**3):.1f} GB"
            disk_info = f"{disk.percent}% of {disk.total / (1024**3):.1f} GB"
        except Exception:
            cpu_info = "N/A"
            ram_info = "N/A"
            disk_info = "N/A"
            
        print(f"│ {secondary}Local OS Platform{reset} : {sys.platform:<51} │")
        print(f"│ {secondary}Python Version{reset}    : {sys.version.split()[0]:<51} │")
        print(f"│ {secondary}Local CPU Load{reset}    : {cpu_info:<51} │")
        print(f"│ {secondary}Local RAM Usage{reset}   : {ram_info:<51} │")
        print(f"│ {secondary}Local Storage{reset}     : {disk_info:<51} │")
        
        if self.remote_url:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            
            remote_status = "UNKNOWN"
            try:
                resp = requests.get(f"{self.remote_url}/status", headers=headers, timeout=3)
                if resp.status_code == 200:
                    remote_status = "ONLINE"
            except Exception:
                remote_status = "OFFLINE"
                
            print(f"├────────────────────────────────────────────────────────────────────────┤")
            print(f"│ {secondary}Remote Node Host{reset}  : {self.remote_url:<51} │")
            print(f"│ {secondary}Remote Node State{reset} : {remote_status:<51} │")
            print(f"│ {secondary}Remote Ping RTT{reset}   : {self.ping_time:<51} │")
            
            remote_facts = "N/A"
            try:
                resp = requests.get(f"{self.remote_url}/memory", headers=headers, timeout=3)
                if resp.status_code == 200:
                    mdata = resp.json()
                    remote_facts = f"{mdata.get('facts', 0)} facts (Total: {mdata.get('total', 0)})"
            except Exception:
                pass
            print(f"│ {secondary}Remote Cognitive{reset}  : {remote_facts:<51} │")
            
        print(f"{primary}└────────────────────────────────────────────────────────────────────────┘{reset}\n")

    def print_memory_facts(self) -> None:
        primary = self.theme["primary"]
        secondary = self.theme["secondary"]
        muted = self.theme["muted"]
        reset = self.theme["reset"]
        success = self.theme["success"]
        
        print(f"\n{primary}┌─── [ COGNITIVE MEMORY FACTS ] ─────────────────────────────────────────┐")
        
        if self.remote_url:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            try:
                resp = requests.get(f"{self.remote_url}/memory", headers=headers, timeout=3)
                if resp.status_code == 200:
                    mdata = resp.json()
                    total = mdata.get("total", 0)
                    facts = mdata.get("facts", 0)
                    recent = mdata.get("recent", [])
                    print(f"│ {secondary}Total Core Objects{reset}: {total:<51} │")
                    print(f"│ {secondary}Factual Associations{reset}: {facts:<49} │")
                    print(f"├────────────────────────────────────────────────────────────────────────┤")
                    print(f"│ {secondary}Recent Recalled Memory Vectors:{reset}                                          │")
                    if recent:
                        if isinstance(recent, dict) and "documents" in recent:
                            docs = recent["documents"]
                            if docs and isinstance(docs, list) and isinstance(docs[0], list):
                                docs = docs[0]
                            for doc in docs[:5]:
                                doc_str = str(doc)[:60]
                                print(f"│   {success}•{reset} {doc_str:<66} │")
                        elif isinstance(recent, list):
                            for doc in recent[:5]:
                                doc_str = str(doc)[:60]
                                print(f"│   {success}•{reset} {doc_str:<66} │")
                        else:
                            print(f"│   {muted}No recent items found in return payload.{reset}                            │")
                    else:
                        print(f"│   {muted}No recent memories established.{reset}                                     │")
                else:
                    print(f"│ {self.theme['danger']}Error: Failed to fetch memory facts (HTTP {resp.status_code}){reset}        │")
            except Exception as e:
                print(f"│ {self.theme['danger']}Error: Connection failed: {e}{reset}                                    │")
        else:
            if self.core and hasattr(self.core, "memory"):
                try:
                    total = self.core.memory.count()
                    results = self.core.memory.collection.get(where={"category": "fact"})
                    facts = len(results["ids"]) if results and "ids" in results else 0
                    print(f"│ {secondary}Total Core Objects{reset}: {total:<51} │")
                    print(f"│ {secondary}Factual Associations{reset}: {facts:<49} │")
                    print(f"├────────────────────────────────────────────────────────────────────────┤")
                    print(f"│ {secondary}Recent Recalled Memory Vectors:{reset}                                          │")
                    recent = self.core.memory.recall("last conversation", top_k=5)
                    if recent and "documents" in recent:
                        docs = recent["documents"]
                        if docs and isinstance(docs, list) and isinstance(docs[0], list):
                            docs = docs[0]
                        for doc in docs[:5]:
                            doc_str = str(doc)[:60]
                            print(f"│   {success}•{reset} {doc_str:<66} │")
                    else:
                        print(f"│   {muted}No recent memories established.{reset}                                     │")
                except Exception as e:
                    print(f"│ {self.theme['danger']}Error: Failed to recall local memory: {e}{reset}                       │")
            else:
                print(f"│ {self.theme['danger']}Error: Core memory module is offline.{reset}                              │")
                
        print(f"{primary}└────────────────────────────────────────────────────────────────────────┘{reset}\n")

    def execute_query(self, user_query: str) -> str:
        if self.remote_url:
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
            
            try:
                resp = requests.post(
                    f"{self.remote_url}/chat",
                    json={"message": user_query},
                    headers=headers,
                    timeout=30
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("response", "").strip()
                elif resp.status_code == 401:
                    return "Error: Unauthorized. Please check your SPARK_ACCESS_TOKEN or --token argument."
                else:
                    resp2 = requests.post(
                        f"{self.remote_url}/api/personal/chat",
                        json={"message": user_query},
                        headers=headers,
                        timeout=10
                    )
                    if resp2.status_code == 200:
                        data2 = resp2.json()
                        return data2.get("response", "").strip()
                    return f"Error: Remote server returned status {resp.status_code} ({resp.reason})"
            except Exception as e:
                return f"Error: Could not reach remote S.P.A.R.K. host: {e}"
        else:
            if not self.core:
                return "Error: Local SparkCore is not initialized."
            try:
                task = {
                    "prompt": user_query,
                    "source": "cli",
                    "include_tools": True,
                }
                result = self.core.llm.execute(task)
                if not isinstance(result, dict):
                    result = {"reply": str(result)}
                
                reply = result.get("reply", "").strip()
                if not reply:
                    reply = "I processed your query but have no response."
                
                try:
                    self.core.memory.log_outcome(
                        {"prompt": user_query, "source": "cli"},
                        result
                    )
                except Exception:
                    pass
                
                return reply
            except Exception as e:
                return f"Error: {e}"

    def run(self) -> int:
        if sys.platform == "win32":
            os.system("cls")
        else:
            os.system("clear")

        self._print_hologram_header()
        
        primary = self.theme["primary"]
        success = self.theme["success"]
        reset = self.theme["reset"]
        
        print("Type '/help' for assistance or '/exit' to terminate session.")
        print()
        
        try:
            while True:
                try:
                    user_input = input(f"{primary}You: {reset}").strip()
                except EOFError:
                    break
                
                if not user_input:
                    continue
                
                # Check for slash directive
                if user_input.startswith("/"):
                    parts = user_input.split()
                    cmd = parts[0].lower()
                    args = parts[1:]
                    
                    if cmd in ("/exit", "/quit"):
                        print(f"{success}Terminating holographic connection. Goodbye!{reset}")
                        break
                        
                    elif cmd == "/help":
                        self.print_help()
                        
                    elif cmd == "/clear":
                        if sys.platform == "win32":
                            os.system("cls")
                        else:
                            os.system("clear")
                        self._update_remote_ping()
                        self._print_hologram_header()
                        
                    elif cmd == "/ping":
                        print(f"{primary}Measuring connection latency...{reset}")
                        self._update_remote_ping()
                        print(f"{success}Current connection latency: {self.ping_time}{reset}")
                        
                    elif cmd == "/sys":
                        self.print_system_info()
                        
                    elif cmd == "/memory":
                        self.print_memory_facts()
                        
                    elif cmd == "/theme":
                        if not args:
                            print(f"{self.theme['warning']}Usage: /theme [cyberpunk | matrix | amber | deepspace]{reset}")
                            print(f"Current theme: {self.theme_name}")
                        else:
                            theme_name = args[0].lower()
                            if theme_name in THEMES:
                                self.theme_name = theme_name
                                self.theme = THEMES[theme_name]
                                primary = self.theme["primary"]
                                success = self.theme["success"]
                                reset = self.theme["reset"]
                                print(f"{success}Theme shifted to {theme_name.upper()}.{reset}")
                            else:
                                print(f"{self.theme['danger']}Unknown theme: {theme_name}. Choose from: cyberpunk, matrix, amber, deepspace{reset}")
                                
                    elif cmd == "/toggle-speed":
                        if self.typewriter_speed == 0.012:
                            self.typewriter_speed = 0.004
                            print(f"{success}Typewriter speed: FAST (4ms){reset}")
                        elif self.typewriter_speed == 0.004:
                            self.typewriter_speed = 0.0
                            print(f"{success}Typewriter speed: INSTANT (0ms){reset}")
                        else:
                            self.typewriter_speed = 0.012
                            print(f"{success}Typewriter speed: NORMAL (12ms){reset}")
                            
                    else:
                        print(f"{self.theme['danger']}Unknown directive: {cmd}. Type /help for assistance.{reset}")
                        
                    print()
                    continue
                
                spinner = Spinner(self.theme)
                spinner.start()
                
                reply = self.execute_query(user_input)
                
                spinner.stop()
                format_and_print_response(reply, self.theme, self.typewriter_speed)
                print()
                
                self.session_count += 1
                
        except KeyboardInterrupt:
            print(f"\n\n{success}Terminating holographic connection. Goodbye!{reset}")
            return 0
        
        return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="SPARK interactive CLI with local/remote modes.")
    parser.add_argument("-r", "--remote", help="URL of the remote SPARK server (e.g. http://localhost:8000)")
    parser.add_argument("-t", "--token", help="Bearer access token for remote authentication")
    args = parser.parse_args()

    remote_url = args.remote or os.getenv("SPARK_REMOTE_URL")
    token = args.token or os.getenv("SPARK_ACCESS_TOKEN")

    try:
        cli = SparkCLI(remote_url=remote_url, token=token)
        return cli.run()
    except Exception as e:
        print(f"\033[91mSPARK CLI Fatal Error: {e}\033[0m")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
