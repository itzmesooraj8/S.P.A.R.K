"""S.P.A.R.K. Bare-Metal Interactive REPL Console.

Enables interactive querying, system debugging, and telemetry monitoring
directly from a unified, security-guarded shell terminal.
"""

from __future__ import annotations

import asyncio
import logging
import sys
import textwrap
import time

from dotenv import load_dotenv

# Ensure environment is loaded
load_dotenv()

# Set up logging configuration to output to file (spark.log is git-ignored)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    filename="spark.log",
    encoding="utf-8",
)

logger = logging.getLogger("SPARK_CLI")

# Core imports
try:
    from security.defense_interceptor import DefensiveInterceptor
except ImportError:
    DefensiveInterceptor = None

try:
    from security.intent_validator import IntentValidator
except ImportError:
    IntentValidator = None

try:
    from core.spark_brain import TOOLS, spark_plan_and_execute
except ImportError:
    TOOLS = []
    async def spark_plan_and_execute(goal: str) -> dict:
        return {"reply": f"Error: Core planning agent could not be loaded. Sanitized query: {goal}"}


def render_response_box(reply: str) -> None:
    """Renders the S.P.A.R.K. planning agent reply inside a premium layout box."""
    width = 76
    print("\n┌" + "─" * (width - 2) + "┐")
    print(f"│ {'S.P.A.R.K. PLANNER RESPONSE':^{(width - 4)}} │")
    print("├" + "─" * (width - 2) + "┤")
    
    wrapper = textwrap.TextWrapper(width=width - 4)
    lines = reply.split("\n")
    for raw_line in lines:
        if not raw_line.strip():
            print(f"│ {' ' * (width - 4)} │")
            continue
        for wrapped_line in wrapper.wrap(raw_line):
            print(f"│ {wrapped_line:<{width - 4}} │")
            
    print("└" + "─" * (width - 2) + "┘\n")


def display_help() -> None:
    """Prints a cleanly aligned list of available multi-agent tools and descriptions."""
    width = 76
    print("\n┌" + "─" * (width - 2) + "┐")
    print(f"│ {'REGISTERED SYSTEM TOOLS':^{(width - 4)}} │")
    print("├" + "─" * (width - 2) + "┤")
    
    if not TOOLS:
        print(f"│ {'No registered tools found in schema dictionary.':<{width - 4}} │")
    else:
        for tool in TOOLS:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "No description provided.")
            
            # Format and wrap tool info
            tool_title = f"- {name}:"
            print(f"│ {tool_title:<{width - 4}} │")
            
            wrapper = textwrap.TextWrapper(width=width - 8, initial_indent="    ", subsequent_indent="    ")
            for desc_line in wrapper.wrap(desc):
                print(f"│ {desc_line:<{width - 4}} │")
            print(f"│ {' ' * (width - 4)} │")

    print("└" + "─" * (width - 2) + "┘\n")


async def run_system_cleanup() -> None:
    """Safely shuts down all background daemons and releases hardware/network locks."""
    print("[SPARK SYSTEM] Initiating safe system cleanups...")
    
    # 1. Terminate audio isolation background daemon
    try:
        from api.audio_daemon import audio_daemon_instance
        audio_daemon_instance.stop()
        print("  - Audio isolation daemon stopped.")
    except Exception:
        pass

    # 2. Terminate FastAPI vitals router daemon
    try:
        from api.server import vitals_router
        vitals_router.stop_daemon()
        print("  - Vitals monitoring daemon stopped.")
    except Exception:
        pass

    # 3. Stop wake word listener hotkeys
    try:
        from core.wake_word import stop_wake_engine
        stop_wake_engine()
        print("  - Wake word engine listeners cleared.")
    except Exception:
        pass
        
    print("[SPARK SYSTEM] Cleanup completed. Exit safe.")


async def main() -> None:
    print("======================================================================")
    print("  S.P.A.R.K. — SENTIENT PROACTIVE AUTONOMOUS RESPONSE KERNEL")
    print("  Interactive Bare-Metal Systems Console Modality [Online]")
    print("======================================================================")
    print("Type 'help' to inspect registered tools. Type 'exit' or 'quit' to close.")

    loop_active = True

    while loop_active:
        try:
            # Read input non-blockingly in async execution frame
            user_input = await asyncio.to_thread(input, "SPARK_SYS_CONSOLE //> ")
            query = user_input.strip()

            if not query:
                continue

            # Escape hooks
            if query.lower() in ["exit", "quit", "shutdown"]:
                loop_active = False
                break

            if query.lower() == "help":
                display_help()
                continue

            print(f"\n[Phase A] Running Defensive Pre-Flight Integrity Checks...")
            # Phase A: Security interceptor checks
            if DefensiveInterceptor is not None:
                try:
                    DefensiveInterceptor.pre_flight_checks()
                    print("  -> Pre-Flight Checks: Staged and Safe.")
                except PermissionError as perm_err:
                    print(f"  [SECURITY ALERT] Pre-Flight Checks Blocked Execution: {perm_err}\n")
                    continue
                except Exception as check_exc:
                    print(f"  [ERROR] Pre-Flight execution error: {check_exc}\n")
                    continue
            else:
                print("  -> Warning: DefensiveInterceptor not imported, skipping pre-flight checks.")

            # Phase B: Intent validation and preambles cleaning
            print(f"[Phase B] Sanitizing conversational preambles...")
            if IntentValidator is not None:
                sanitized_query = IntentValidator.sanitize(query)
                print(f"  -> Lexical Cleaned Query: '{sanitized_query}'")
            else:
                sanitized_query = query
                print("  -> Warning: IntentValidator not imported, skipping preambles sanitization.")

            if not sanitized_query.strip():
                print("  -> Resulting query is empty. Aborting turn.\n")
                continue

            # Phase C: Main planning agent execution
            print(f"[Phase C] Dispatching query directly to central multi-agent planner...")
            try:
                result = await spark_plan_and_execute(sanitized_query)
                reply = result.get("reply", "No reply was received from planning agent.")
                render_response_box(reply)
            except Exception as plan_exc:
                print(f"  [PLANNER EXCEPTION] Turn processing failed: {plan_exc}\n")

        except KeyboardInterrupt:
            # Intercept Ctrl+C safely without dropping system state
            print("\n\n[SPARK CONSOLE] WARNING: KeyboardInterrupt intercepted.")
            print("To exit safely, please type 'exit' or press Ctrl+C once more if necessary.")
            continue
        except EOFError:
            # Handle Ctrl+D EOF safely
            print("\n[SPARK CONSOLE] EOF reached. Initiating safe exit.")
            break
        except Exception as err:
            logger.error("CLI REPL error: %s", err, exc_info=True)
            print(f"[CONSOLE RUNTIME ERROR] Unexpected loop error: {err}\n")

    # Exit cleanup
    await run_system_cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # Final catch-all for keyboard interrupts at initialization
        print("\n[SPARK CONSOLE] Terminal console shut down cleanly.")
        sys.exit(0)
