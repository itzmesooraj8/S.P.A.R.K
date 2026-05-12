from __future__ import annotations

import ast
import logging
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from core.generated_tools import publish_generated_tool

log = logging.getLogger("spark.tool_forge")

FORGE_DIR = Path("spark_dev_memory/tool_forge")
FORGE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMPORTS = {
    "json",
    "math",
    "statistics",
    "datetime",
    "time",
    "re",
    "typing",
    "pathlib",
    "collections",
    "itertools",
    "functools",
    "string",
    "random",
    "tools",
}

FORBIDDEN_NAMES = {"eval", "exec", "compile", "__import__", "input"}
FORBIDDEN_ATTRS = {
    ("os", "system"),
    ("os", "popen"),
    ("subprocess", "Popen"),
    ("subprocess", "run"),
    ("subprocess", "call"),
    ("shutil", "rmtree"),
    ("socket", "socket"),
    ("ctypes", "CDLL"),
    ("ctypes", "windll"),
}


@dataclass(slots=True)
class ForgeResult:
    name: str
    path: str
    approved: bool
    reason: str


def _node_to_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_node_to_name(node.value)}.{node.attr}"
    return ""


def validate_tool_code(code: str) -> tuple[bool, str]:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"Syntax error: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root not in ALLOWED_IMPORTS:
                    return False, f"Import not allowed: {alias.name}"
        elif isinstance(node, ast.Call):
            name = _node_to_name(node.func)
            root = name.split(".", 1)[0]
            if root in FORBIDDEN_NAMES:
                return False, f"Forbidden call: {name}"
            if (root, name.split(".")[-1]) in FORBIDDEN_ATTRS:
                return False, f"Forbidden call: {name}"
    return True, "Approved"


def forge_tool(name: str, code: str, description: str = "") -> ForgeResult:
    approved, reason = validate_tool_code(code)
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]+", "_", name).strip("_") or "forged_tool"
    path = FORGE_DIR / f"{safe_name}.py"
    if approved:
        path.write_text(code, encoding="utf-8")
        try:
            publish_generated_tool(safe_name, code)
        except Exception as exc:
            log.warning("Failed to publish generated tool '%s': %s", safe_name, exc)
    return ForgeResult(name=safe_name, path=str(path), approved=approved, reason=reason)


def run_forged_tool(path: str, argument: str = "", timeout: int = 15) -> str:
    script_path = Path(path)
    if not script_path.exists():
        return f"Forge error: {script_path} does not exist"

    result = subprocess.run(
        [sys.executable, str(script_path), argument],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    stdout = result.stdout.strip()
    stderr = result.stderr.strip()
    if result.returncode != 0:
        return f"Forge execution failed: {stderr or stdout or 'unknown error'}"
    return stdout or stderr or "Forge tool completed successfully"