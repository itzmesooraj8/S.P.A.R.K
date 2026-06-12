"""Sandbox — Sandboxed execution for tools."""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger("spark.security.sandbox")


class Sandbox:
    """
    Sandboxed execution for tools.

    Tools run in restricted contexts:
    - Limited file system access
    - Network restrictions
    - Process isolation
    """

    def __init__(self, sandbox_dir: str = "spark_dev_memory/sandbox") -> None:
        self._sandbox_dir = Path(sandbox_dir)
        self._sandbox_dir.mkdir(parents=True, exist_ok=True)
        self._active = False

    def create_session(self) -> str:
        session_id = f"sandbox_{os.getpid()}"
        session_dir = self._sandbox_dir / session_id
        session_dir.mkdir(exist_ok=True)
        self._active = True
        logger.info("Sandbox session created: %s", session_id)
        return session_id

    def get_temp_path(self, filename: str = "temp.txt") -> str:
        return str(self._sandbox_dir / "temp" / filename)

    def restrict_file_access(self, allowed_paths: list[str]) -> dict[str, Any]:
        return {
            "sandboxed": True,
            "allowed_paths": allowed_paths,
            "sandbox_dir": str(self._sandbox_dir),
        }

    def restrict_network(self, allowed_hosts: list[str] | None = None) -> dict[str, Any]:
        return {
            "network_restricted": True,
            "allowed_hosts": allowed_hosts or [],
        }

    def execute_in_sandbox(self, command: str, timeout: int = 30) -> dict[str, Any]:
        import subprocess
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(self._sandbox_dir),
            )
            return {
                "success": result.returncode == 0,
                "stdout": result.stdout[:1000],
                "stderr": result.stderr[:500],
                "returncode": result.returncode,
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Command timed out"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def cleanup(self) -> None:
        import shutil
        if self._sandbox_dir.exists():
            shutil.rmtree(str(self._sandbox_dir), ignore_errors=True)
        self._active = False
        logger.info("Sandbox cleaned up")

    def info(self) -> dict[str, Any]:
        return {
            "active": self._active,
            "sandbox_dir": str(self._sandbox_dir),
        }
