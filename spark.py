from __future__ import annotations

import argparse
import importlib.machinery
import sys
from pathlib import Path
from types import ModuleType


def _bootstrap_package() -> None:
    package_dir = Path(__file__).with_name("spark")
    package = ModuleType("spark")
    package.__path__ = [str(package_dir)]
    package.__package__ = "spark"
    package.__file__ = str(package_dir / "__init__.py")
    package.__spec__ = importlib.machinery.ModuleSpec("spark", loader=None, is_package=True)
    package.__spec__.submodule_search_locations = [str(package_dir)]
    sys.modules.setdefault("spark", package)


# Bootstrap synthetic package on module import (for spark_cli.py and others)
_bootstrap_package()


def main() -> int:
    _bootstrap_package()
    parser = argparse.ArgumentParser(description="SPARK minimal runtime")
    parser.add_argument("--once", action="store_true", help="Run one autonomous cycle and exit")
    parser.add_argument("--voice", action="store_true", help="Run the live mic -> Whisper -> LLM -> speak loop")
    parser.add_argument("--voice-once", action="store_true", help="Run one voice interaction and exit")
    parser.add_argument("--dry-run", action="store_true", help="Load config and show startup status")
    args = parser.parse_args()

    from spark.core import SparkCore, load_config, main as run_main

    if args.dry_run:
        config = load_config()
        print(f"SPARK config loaded: {bool(config)}")
        print(f"Loop interval: {config.get('loop_interval_seconds', 5)}s")
        print(f"Generated tools dir: {config.get('tools', {}).get('generated_dir', 'tools/generated')}")
        return 0

    core = SparkCore()

    if args.voice_once:
        result = core.run_voice_once()
        if result is not None:
            print(result.get("reply", ""))
        else:
            print("No speech detected.")
        return 0

    if args.voice:
        core.run_voice_loop()
        return 0

    if args.once:
        return run_main(once=True)

    core.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
