"""File Automation — File system operations."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.automation.file_control")


class FileAutomation:
    """Automates file system operations."""

    def read_file(self, path: str) -> dict[str, Any]:
        try:
            p = Path(path)
            if p.exists():
                content = p.read_text(encoding="utf-8")
                return {"success": True, "content": content, "size": len(content)}
            return {"success": False, "error": "File not found"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def write_file(self, path: str, content: str) -> dict[str, Any]:
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return {"success": True, "path": path, "size": len(content)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def list_directory(self, path: str = ".") -> dict[str, Any]:
        try:
            p = Path(path)
            if p.is_dir():
                items = [{"name": item.name, "is_dir": item.is_dir()} for item in p.iterdir()]
                return {"success": True, "items": items, "count": len(items)}
            return {"success": False, "error": "Not a directory"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def search_files(self, pattern: str, path: str = ".") -> dict[str, Any]:
        try:
            matches = list(Path(path).glob(pattern))
            return {"success": True, "matches": [str(m) for m in matches], "count": len(matches)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
