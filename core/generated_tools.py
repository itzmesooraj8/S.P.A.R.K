from __future__ import annotations

import importlib.util
import json
import logging
import re
from dataclasses import dataclass
from hashlib import sha1
from pathlib import Path
from typing import Any

try:
    from security.action_guard import guard_action
except Exception:
    # Fallback dummy guard if security package not available
    def guard_action(tool_name, **kwargs):
        return True, "allowed", None


log = logging.getLogger("spark.generated_tools")

GENERATED_TOOL_DIR = Path("tools/generated")
GENERATED_TOOL_DIR.mkdir(parents=True, exist_ok=True)


@dataclass(slots=True)
class GeneratedTool:
    name: str
    description: str
    parameters: dict[str, Any]
    path: Path
    module: Any


def _module_name(path: Path) -> str:
    digest = sha1(str(path).encode("utf-8")).hexdigest()[:12]
    return f"spark_generated_{path.stem}_{digest}"


def _load_module(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(_module_name(path), path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load generated tool: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _extract_spec(module: Any, path: Path) -> tuple[str, str, dict[str, Any]] | None:
    spec = getattr(module, "TOOL_SPEC", None)
    if isinstance(spec, dict):
        name = str(spec.get("name") or path.stem).strip() or path.stem
        description = str(spec.get("description") or f"Generated tool from {path.stem}").strip()
        parameters = spec.get("parameters")
        if not isinstance(parameters, dict):
            parameters = {"type": "object", "properties": {"argument": {"type": "string"}}, "required": []}
        return name, description, parameters

    if callable(getattr(module, "run", None)):
        return path.stem, f"Generated tool from {path.stem}", {"type": "object", "properties": {"argument": {"type": "string"}}, "required": []}

    return None


def discover_generated_tools() -> list[GeneratedTool]:
    tools: list[GeneratedTool] = []
    for path in sorted(GENERATED_TOOL_DIR.glob("*.py")):
        if path.name == "__init__.py":
            continue
        try:
            module = _load_module(path)
            spec = _extract_spec(module, path)
            if not spec:
                continue
            name, description, parameters = spec
            tools.append(GeneratedTool(name=name, description=description, parameters=parameters, path=path, module=module))
        except Exception as exc:
            log.info("Skipping generated tool '%s': %s", path.name, exc)
    return tools


def load_generated_tool_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for tool in discover_generated_tools():
        specs.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
        )
    return specs


def run_generated_tool(tool_name: str, argument: Any) -> Any:
    for tool in discover_generated_tools():
        if tool.name != tool_name:
            continue
        runner = getattr(tool.module, "run", None)
        if not callable(runner):
            raise AttributeError(f"Generated tool '{tool_name}' is missing run()")
        # Sanitize / normalize argument payload
        if isinstance(argument, (dict, list)):
            payload = json.dumps(argument, ensure_ascii=False)
        else:
            payload = str(argument)

        # Security check: ask guard if this tool may run with given payload
        try:
            allowed, msg, meta = guard_action(tool.name, argument=payload)
        except Exception:
            allowed, msg, meta = True, "guard_failed_open", None

        if not allowed:
            raise PermissionError(f"Execution of tool '{tool_name}' blocked by guard: {msg}")

        return runner(payload)
    raise KeyError(tool_name)


def publish_generated_tool(name: str, code: str) -> Path:
    safe_name = re.sub(r"[^a-zA-Z0-9_\-]+", "_", name).strip("_") or "generated_tool"
    path = GENERATED_TOOL_DIR / f"{safe_name}.py"
    path.write_text(code, encoding="utf-8")
    return path
