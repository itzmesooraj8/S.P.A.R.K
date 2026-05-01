"""
spark_cli.py — S.P.A.R.K. Command Line Interface
Provides a direct text-based interface to the SPARK cognitive core.
No voice, no HUD — pure terminal interaction.

Usage:
    python spark_cli.py                    # interactive REPL
    python spark_cli.py "your query"       # single-shot mode
    python spark_cli.py --no-memory        # session without ChromaDB
    python spark_cli.py --debug            # verbose logging
    python spark_cli.py --help             # show this help
"""

import sys
import os
import argparse
import logging

# Ensure project root is on the path regardless of where we run from
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logger = logging.getLogger("SPARK_CLI")


# ── ANSI color codes ─────────────────────────────────────────────────────────
class C:
    RESET   = "\033[0m"
    BOLD    = "\033[1m"
    DIM     = "\033[2m"
    CYAN    = "\033[96m"
    AMBER   = "\033[33m"
    GREEN   = "\033[92m"
    RED     = "\033[91m"
    WHITE   = "\033[97m"
    BLUE    = "\033[94m"
    MAGENTA = "\033[95m"

SPARK_BANNER = f"""
{C.CYAN}{C.BOLD}
  ███████╗██████╗  █████╗ ██████╗ ██╗  ██╗
  ██╔════╝██╔══██╗██╔══██╗██╔══██╗██║ ██╔╝
  ███████╗██████╔╝███████║██████╔╝█████╔╝ 
  ╚════██║██╔═══╝ ██╔══██║██╔══██╗██╔═██╗ 
  ███████║██║     ██║  ██║██║  ██║██║  ██╗
  ╚══════╝╚═╝     ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝
{C.RESET}
{C.AMBER}  Sovereign Personal AI Runtime Kernel{C.RESET}
{C.DIM}  CLI Mode — Type your query or 'exit' to quit{C.RESET}
{C.DIM}  Commands: :memory | :tools | :clear | :reminders | :help{C.RESET}
"""

CLI_HELP = f"""
{C.BOLD}S.P.A.R.K. CLI Commands:{C.RESET}
  {C.CYAN}:memory{C.RESET}       — Show last N stored memory entries
  {C.CYAN}:tools{C.RESET}        — List all available tools
  {C.CYAN}:clear{C.RESET}        — Clear terminal screen
  {C.CYAN}:reminders{C.RESET}    — Show pending scheduled reminders
  {C.CYAN}:remind <N> <msg>{C.RESET} — Set a reminder in N seconds
  {C.CYAN}:sysmon{C.RESET}       — Show current system metrics
  {C.CYAN}:help{C.RESET}         — Show this help
  {C.CYAN}exit / quit{C.RESET}   — Exit SPARK CLI
"""


def setup_logging(debug: bool):
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s"
    )
    # Suppress noisy third-party loggers
    for lib in ["httpx", "chromadb", "urllib3", "httpcore", "groq"]:
        logging.getLogger(lib).setLevel(logging.ERROR)


def print_spark(text: str):
    """Print SPARK's response with amber styling."""
    print(f"\n{C.CYAN}◈ SPARK{C.RESET}  {C.WHITE}{text}{C.RESET}\n")


def print_info(text: str):
    print(f"{C.DIM}  {text}{C.RESET}")


def print_error(text: str):
    print(f"{C.RED}  ✗ {text}{C.RESET}")


def print_success(text: str):
    print(f"{C.GREEN}  ✓ {text}{C.RESET}")


def handle_cli_command(cmd: str, agent, memory, scheduler) -> bool:
    """
    Handle special CLI commands (prefixed with :).
    Returns True if handled, False if should be passed to agent.
    """
    parts = cmd.strip().split()
    command = parts[0].lower() if parts else ""

    if command == ":help":
        print(CLI_HELP)
        return True

    elif command == ":clear":
        os.system("cls" if os.name == "nt" else "clear")
        print(SPARK_BANNER)
        return True

    elif command == ":memory":
        try:
            results = memory.collection.get(include=["documents", "metadatas"])
            docs = results.get("documents", [])[-10:]
            metas = results.get("metadatas", [])[-10:]
            if not docs:
                print_info("No memories stored yet.")
            else:
                print(f"\n{C.BOLD}  Last {len(docs)} memory entries:{C.RESET}")
                for i, (doc, meta) in enumerate(zip(docs, metas)):
                    role = meta.get("role", "?") if meta else "?"
                    role_color = C.CYAN if role == "assistant" else C.AMBER
                    print(f"  {C.DIM}[{i+1}]{C.RESET} {role_color}{role:10}{C.RESET} {doc[:80]}{'...' if len(doc) > 80 else ''}")
                print()
        except Exception as e:
            print_error(f"Could not read memory: {e}")
        return True

    elif command == ":tools":
        try:
            from core.main import tools  # import registered tools dict
            print(f"\n{C.BOLD}  Available Tools:{C.RESET}")
            for name, info in tools.items():
                desc = info.get("description", "No description")[:60]
                print(f"  {C.CYAN}• {name:25}{C.RESET} {C.DIM}{desc}{C.RESET}")
            print()
        except Exception as e:
            print_error(f"Could not load tools list: {e}")
        return True

    elif command == ":sysmon":
        try:
            from tools.sysmon import get_raw_metrics
            m = get_raw_metrics()
            print(f"\n{C.BOLD}  System Metrics:{C.RESET}")
            print(f"  {C.CYAN}CPU{C.RESET}      {m.get('cpu_percent', '?')}%")
            print(f"  {C.CYAN}RAM{C.RESET}      {m.get('ram_percent', '?')}%  ({m.get('ram_used_gb', '?')} / {m.get('ram_total_gb', '?')} GB)")
            print(f"  {C.CYAN}Disk{C.RESET}     {m.get('disk_percent', '?')}%")
            print(f"  {C.CYAN}GPU{C.RESET}      {m.get('gpu_name', 'N/A')}  {m.get('gpu_util', '?')}%  VRAM: {m.get('vram_used_mb', '?')} MB")
            print()
        except Exception as e:
            print_error(f"sysmon error: {e}")
        return True

    elif command == ":reminders":
        try:
            from core.scheduler import list_reminders
            jobs = list_reminders()
            if not jobs:
                print_info("No pending reminders.")
            else:
                print(f"\n{C.BOLD}  Pending Reminders:{C.RESET}")
                for j in jobs:
                    print(f"  {C.CYAN}• {j['id'][:30]}{C.RESET}  fires at {j['next_run']}")
                    if j.get('args'):
                        print(f"    {C.DIM}message: {j['args'][0]}{C.RESET}")
                print()
        except Exception as e:
            print_error(f"Could not list reminders: {e}")
        return True

    elif command == ":remind":
        # :remind <seconds> <message...>
        if len(parts) < 3:
            print_error("Usage: :remind <seconds> <your message>")
            return True
        try:
            delay = int(parts[1])
            message = " ".join(parts[2:])
            from core.scheduler import set_reminder, init_scheduler
            init_scheduler()  # ensure running in CLI mode
            result = set_reminder(message, delay)
            print_success(result)
        except ValueError:
            print_error("seconds must be an integer. Usage: :remind 120 Check the logs")
        except Exception as e:
            print_error(f"Could not set reminder: {e}")
        return True

    return False  # not a CLI command


def run_interactive(agent, memory, scheduler, no_memory: bool):
    """Main REPL loop."""
    print(SPARK_BANNER)
    print_info("All systems nominal. Ready for your command, sir.")
    print()

    while True:
        try:
            raw = input(f"{C.AMBER}You ›{C.RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{C.DIM}  Signing off. — S.P.A.R.K.{C.RESET}\n")
            break

        if not raw:
            continue

        if raw.lower() in ("exit", "quit", "bye", "q"):
            print(f"\n{C.DIM}  Signing off. — S.P.A.R.K.{C.RESET}\n")
            break

        # CLI command?
        if raw.startswith(":"):
            handle_cli_command(raw, agent, memory, scheduler)
            continue

        # Pass to SPARK cognitive engine
        try:
            print(f"{C.DIM}  Thinking...{C.RESET}", end="\r", flush=True)
            response = agent.query(raw, voice_output=False)
            print(" " * 20, end="\r")  # clear "Thinking..."
            print_spark(response)
        except KeyboardInterrupt:
            print(f"\n{C.DIM}  Interrupted.{C.RESET}")
        except Exception as e:
            print_error(f"Agent error: {e}")
            logging.debug("Full traceback:", exc_info=True)


def run_single_shot(query: str, agent, no_memory: bool):
    """Execute a single query and print result — useful for piping/scripting."""
    try:
        response = agent.query(query, voice_output=False)
        print(response)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


class CLIAgent:
    """
    Lightweight wrapper around SPARK's cognitive core for CLI use.
    Reuses all the same tools, memory, and LLM — just no voice output.
    """
    def __init__(self, memory, no_memory: bool = False):
        self._memory = memory
        self._no_memory = no_memory
        self._groq_client = None
        self._init_llm()

    def _init_llm(self):
        try:
            from groq import Groq
            from dotenv import load_dotenv
            load_dotenv()
            self._groq_client = Groq()
            logger.info("[CLI] Groq client initialized.")
        except Exception as e:
            logger.warning(f"[CLI] Groq init failed: {e}")

    def query(self, text: str, voice_output: bool = False) -> str:
        """
        Send a query through the full SPARK pipeline.
        Reuses tool execution and memory from core/main.py.
        """
        try:
            # Import the run_agent_turn function from core/main.py if available
            from core.main import run_agent_turn
            return run_agent_turn(text, voice_output=False, cli_mode=True)
        except (ImportError, AttributeError):
            # Fallback: direct Groq call if run_agent_turn isn't extracted yet
            return self._direct_query(text)

    def _direct_query(self, text: str) -> str:
        """Direct LLM query fallback."""
        if not self._groq_client:
            return "Error: LLM client not initialized. Check your .env file."
        try:
            # Fetch relevant memory context
            context = ""
            if not self._no_memory and self._memory:
                try:
                    results = self._memory.query(text, n_results=5)
                    if results and results.get("documents"):
                        docs = results["documents"][0]
                        context = "Relevant context from memory:\n" + "\n".join(f"- {d}" for d in docs[:3]) + "\n\n"
                except Exception:
                    pass

            system_prompt = (
                "You are S.P.A.R.K. — Sovereign Personal AI Runtime Kernel. "
                "A highly capable, precise personal AI assistant. "
                "You are running in CLI mode — be concise, direct, and helpful. "
                "Respond in plain text (no markdown unless specifically asked)."
            )

            messages = []
            if context:
                messages.append({"role": "user", "content": context})
                messages.append({"role": "assistant", "content": "Context loaded."})
            messages.append({"role": "user", "content": text})

            response = self._groq_client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "system", "content": system_prompt}] + messages,
                max_tokens=1024
            )
            return response.choices[0].message.content.strip()

        except Exception as e:
            return f"Error processing request: {e}"


def main():
    parser = argparse.ArgumentParser(
        description="S.P.A.R.K. CLI — Sovereign Personal AI Runtime Kernel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "query",
        nargs="?",
        help="Single query to execute (omit for interactive mode)"
    )
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Disable ChromaDB memory for this session"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug logging"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="S.P.A.R.K. CLI v1.0.0 — Phase 03"
    )

    args = parser.parse_args()
    setup_logging(args.debug)

    # Initialize memory
    memory = None
    if not args.no_memory:
        try:
            from core.vector_store import SparkVectorMemory
            memory = SparkVectorMemory()
        except Exception as e:
            logging.warning(f"Memory init failed (running without memory): {e}")

    # Initialize scheduler (for :remind commands in CLI)
    scheduler = None
    try:
        from core.scheduler import init_scheduler
        scheduler = init_scheduler(voice=None)  # no voice in CLI
    except Exception as e:
        logging.debug(f"Scheduler init skipped: {e}")

    # Build CLI agent
    agent = CLIAgent(memory=memory, no_memory=args.no_memory)

    # Run
    if args.query:
        run_single_shot(args.query, agent, args.no_memory)
    else:
        run_interactive(agent, memory, scheduler, args.no_memory)


if __name__ == "__main__":
    main()
