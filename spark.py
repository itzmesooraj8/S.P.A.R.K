from __future__ import annotations

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
    from spark_cli import main as cli_main

    return cli_main()


if __name__ == "__main__":
    raise SystemExit(main())
