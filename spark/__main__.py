"""
S.P.A.R.K. — AI Operating System v2.0
Main entry point for the complete modular architecture.
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


def main() -> int:
    os = SparkOS()
    os.initialize()
    logger.info("SPARK AI Operating System v2.0 ready")
    print(os.run_dashboard())
    return 0


def process_command(user_input: str) -> str:
    os = SparkOS()
    os.initialize()
    result = asyncio.run(os.process(user_input))
    return str(result.get("reply", ""))


if __name__ == "__main__":
    raise SystemExit(main())
