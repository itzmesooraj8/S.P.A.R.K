"""Distributed launch integrity guard for Phase 3 configuration state."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import threading
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("SPARK_SWARM_GUARD")


class SwarmProtocolGuard:
    """Continuously validates runtime manifests against a trusted local mirror."""

    def __init__(
        self,
        workspace_dir: Optional[str] = None,
        mirror_dir: Optional[str] = None,
        monitored_files: Optional[list[str]] = None,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self.workspace_dir = Path(workspace_dir or os.getcwd()).resolve()
        self.mirror_dir = Path(mirror_dir or self.workspace_dir / "config" / "backups").resolve()
        self.monitored_files = monitored_files or ["config.json", "config/hybrid_strategy.json"]
        self.poll_interval_seconds = poll_interval_seconds
        self.expected_hashes: Dict[str, str] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._bootstrap_signatures()

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with open(path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def _candidate_paths(self, relative_path: str) -> tuple[Path, Path]:
        workspace_path = (self.workspace_dir / relative_path).resolve()
        mirror_path = (self.mirror_dir / relative_path).resolve()
        return workspace_path, mirror_path

    def _bootstrap_signatures(self) -> None:
        self.mirror_dir.mkdir(parents=True, exist_ok=True)
        for relative_path in self.monitored_files:
            workspace_path, mirror_path = self._candidate_paths(relative_path)
            source = mirror_path if mirror_path.exists() else workspace_path
            if not source.exists():
                continue
            if not mirror_path.exists():
                mirror_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, mirror_path)
            self.expected_hashes[relative_path] = self._sha256(mirror_path)

    def verify_once(self) -> Dict[str, Any]:
        restored: list[str] = []
        mismatched: list[str] = []
        for relative_path, expected_hash in self.expected_hashes.items():
            workspace_path, mirror_path = self._candidate_paths(relative_path)
            candidate = workspace_path if workspace_path.exists() else mirror_path
            if not candidate.exists():
                raise PermissionError(f"Missing protected manifest: {relative_path}")

            current_hash = self._sha256(candidate)
            if current_hash != expected_hash:
                mismatched.append(relative_path)
                if mirror_path.exists():
                    workspace_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(mirror_path, workspace_path)
                    restored.append(relative_path)
                    if self._sha256(workspace_path) != expected_hash:
                        raise PermissionError(f"Integrity restore failed for {relative_path}")
                else:
                    raise PermissionError(f"No mirror available for {relative_path}")

        return {"valid": not mismatched, "restored": restored, "mismatched": mismatched}

    def enforce_launch_gate(self) -> None:
        result = self.verify_once()
        if not result["valid"]:
            raise PermissionError("Swarm protocol validation failed.")

    def build_isolated_launch_env(self) -> Dict[str, str]:
        env = os.environ.copy()
        env["SPARK_EXECUTION_MODE"] = "fallback_isolated"
        env["SPARK_CONFIG_GUARDED"] = "1"
        env["LLM_BACKEND"] = "ollama"
        return env

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True, name="swarm-guard")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                self.verify_once()
            except Exception as exc:
                logger.error(f"Swarm guard detected integrity violation: {exc}")
            time.sleep(self.poll_interval_seconds)


def build_guarded_launch_context(workspace_dir: Optional[str] = None) -> SwarmProtocolGuard:
    """Convenience helper for launch scripts."""
    return SwarmProtocolGuard(workspace_dir=workspace_dir)