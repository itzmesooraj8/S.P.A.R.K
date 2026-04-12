# S.P.A.R.K. Core Package

from pathlib import Path
import sys

# Ensure legacy absolute imports like from ws.manager import ... resolve
# when modules are imported as spark_core.* (e.g., in CI/test contexts).
_CORE_DIR = str(Path(__file__).resolve().parent)
if _CORE_DIR not in sys.path:
    sys.path.insert(0, _CORE_DIR)
