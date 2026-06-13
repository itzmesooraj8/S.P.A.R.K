"""
S.P.A.R.K. — AI Operating System v2.0
Main entry point with interactive CLI.
"""

from __future__ import annotations

import asyncio
import logging
import sys

from spark.os import SparkOS

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("SPARK")


def print_banner() -> None:
    print("=" * 60)
    print("  S.P.A.R.K. AI OPERATING SYSTEM")
    print("  Type 'help' for commands, 'quit' to exit")
    print("=" * 60)


def print_help() -> None:
    print("""
Commands:
  <message>     Chat with SPARK
  dashboard     Show system dashboard
  status        Show system health
  goals         Show active goals
  memory        Show memory stats
  agents        Show agent status
  world         Show world model
  skills        Show learned skills
  decisions     Show decision log
  clear         Clear screen
  help          Show this help
  quit          Exit SPARK
""")


async def interactive_loop(os: SparkOS) -> None:
    """Main interactive loop."""
    print_banner()

    while True:
        try:
            user_input = await asyncio.get_event_loop().run_in_executor(
                None, lambda: input("\nSPARK > ").strip()
            )
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye, sir.")
            break

        if not user_input:
            continue

        lower = user_input.lower()

        if lower in ("quit", "exit", "q"):
            print("Shutting down SPARK...")
            os.shutdown()
            break

        if lower == "help":
            print_help()
            continue

        if lower == "clear":
            print("\033c", end="")
            continue

        if lower == "dashboard":
            print(os.run_dashboard())
            continue

        if lower == "status":
            health = os.env_awareness.get_health()
            print(f"Status: {health.get('status', 'unknown')}")
            print(f"CPU: {health.get('cpu_percent', '?')}%")
            print(f"Memory: {health.get('memory_percent', '?')}%")
            continue

        if lower == "goals":
            stats = os.goal_engine.stats()
            print(f"Active goals: {stats.get('active', 0)}")
            for g in stats.get("goals", []):
                print(f"  - {g.get('desc', '?')} [{g.get('status', '?')}]")
            continue

        if lower == "memory":
            print(f"Semantic: {os.semantic_memory.count()}")
            print(f"Episodic: {os.episodic_memory.count()}")
            wm = os.working_memory.snapshot()
            print(f"Working objective: {wm.get('objective', {}).get('description', 'None')}")
            continue

        if lower == "agents":
            agents = [os.planner_agent, os.executor_agent, os.memory_agent, os.reflection_agent, os.observer_agent]
            for agent in agents:
                info = agent.info()
                print(f"  {info['name']}: {info['status']}")
            continue

        if lower == "world":
            snapshot = os.world_model.snapshot()
            print(f"Activity: {snapshot.get('current_activity', 'unknown')}")
            predictions = snapshot.get("predictions", [])
            for p in predictions:
                print(f"  Predicted: {p.get('need', '?')} ({p.get('confidence', 0):.0%})")
            continue

        if lower == "skills":
            skills = os.skill_registry.list_all()
            if not skills:
                print("No skills learned yet.")
            for s in skills:
                print(f"  {s.get('name', '?')}: {s.get('use_count', 0)} uses, {s.get('success_rate', 0):.0%} success")
            continue

        if lower == "decisions":
            decisions = os.decision_log.recent(10)
            if not decisions:
                print("No decisions recorded.")
            for d in decisions:
                print(f"  [{d.get('action', '?')}] {d.get('reason', '?')[:60]}")
            continue

        # Process as chat message
        try:
            result = await os.process(user_input, source="cli")
            reply = result.get("reply", "No response")
            print(f"\n{reply}")
        except Exception as exc:
            print(f"\nError: {exc}")


def main() -> int:
    os = SparkOS()
    os.initialize()
    logger.info("SPARK AI Operating System v2.0 ready")
    asyncio.run(interactive_loop(os))
    return 0


def process_command(user_input: str) -> str:
    os = SparkOS()
    os.initialize()
    result = asyncio.run(os.process(user_input))
    return str(result.get("reply", ""))


if __name__ == "__main__":
    raise SystemExit(main())
