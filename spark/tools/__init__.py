from __future__ import annotations

import importlib.util
import json
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any


@dataclass
class ToolRecord:
    name: str
    path: Path
    module: ModuleType
    spec: dict[str, Any] | None


class ToolRegistry:
    def __init__(self, config: dict[str, Any]):
        tools_config = config.get("tools", {}) if isinstance(config, dict) else {}
        generated_dir = tools_config.get("generated_dir", "tools/generated")
        self.generated_dir = Path(generated_dir)
        self.generated_dir.mkdir(parents=True, exist_ok=True)
        self._records: dict[str, ToolRecord] = {}
        self.refresh()

    def refresh(self) -> dict[str, ToolRecord]:
        records: dict[str, ToolRecord] = {}
        for path in sorted(self.generated_dir.glob("*.py")):
            if path.name == "__init__.py":
                continue
            module_name = f"spark_generated_{path.stem}_{path.stat().st_mtime_ns}"
            spec = importlib.util.spec_from_file_location(module_name, path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            tool_spec = getattr(module, "TOOL_SPEC", None)
            tool_name = self._tool_name(path, tool_spec)
            if tool_name:
                records[tool_name] = ToolRecord(tool_name, path, module, tool_spec if isinstance(tool_spec, dict) else None)
        self._records = records
        return records

    def list_tools(self) -> list[dict[str, Any]]:
        self.refresh()
        return [record.spec or {"name": record.name, "path": str(record.path)} for record in self._records.values()]

    def call(self, name: str, payload: dict[str, Any] | None = None) -> Any:
        self.refresh()
        record = self._records.get(name)
        if record is None:
            raise KeyError(f"Unknown generated tool: {name}")
        if hasattr(record.module, "run"):
            return record.module.run(payload or {})
        if hasattr(record.module, "main"):
            return record.module.main(payload or {})
        raise AttributeError(f"Generated tool {name} has no run() or main()")

    def _tool_name(self, path: Path, tool_spec: dict[str, Any] | None) -> str | None:
        if isinstance(tool_spec, dict) and tool_spec.get("name"):
            return str(tool_spec["name"])
        return path.stem
