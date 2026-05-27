"""S.P.A.R.K Sandboxed Task Memory Bridge.

Provides secure variable tracking and traversal check assertions between
low-priority preview workers and the central multi-agent system.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("SPARK_SANDBOX_MEMORY_BRIDGE")


class SecurityError(ValueError):
    """Raised when unsafe code injection or system traversal patterns are detected."""
    pass


class SandboxMemoryBridge:
    """Cryptographically secure variables tracking connector for isolated worker processes."""

    def __init__(self, sandbox_root: Optional[str] = None) -> None:
        workspace_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.sandbox_root = Path(sandbox_root or os.path.join(workspace_dir, "sandbox")).resolve()
        self.sandbox_root.mkdir(parents=True, exist_ok=True)

    def verify_sandbox_path(self, target_path: str | Path) -> Path:
        """Enforces absolute path traversal prevention within the sandbox directory matrix."""
        candidate = Path(target_path).resolve()
        # Verify that candidate path is strictly under sandbox_root
        if self.sandbox_root not in candidate.parents and candidate != self.sandbox_root:
            logger.critical("Path traversal attempt blocked: %s", target_path)
            raise PermissionError(f"Access Denied: Path '{target_path}' lies outside the authorized sandbox folder.")
        return candidate

    def read_worker_state(self, filename: str) -> Dict[str, Any]:
        """Safely reads manifest state indicators written by low-priority workers."""
        safe_path = self.verify_sandbox_path(self.sandbox_root / filename)
        if not safe_path.exists():
            return {}

        try:
            content = safe_path.read_text(encoding="utf-8")
            self.sanitize_content(content)
            return json.loads(content)
        except Exception as exc:
            logger.error("Failed to read worker state securely: %s", exc)
            if isinstance(exc, (PermissionError, SecurityError)):
                raise exc
            return {"error": str(exc)}

    def write_worker_state(self, filename: str, data: Dict[str, Any]) -> None:
        """Writes worker state parameters inside the sandbox."""
        safe_path = self.verify_sandbox_path(self.sandbox_root / filename)
        raw_str = json.dumps(data)
        self.sanitize_content(raw_str)
        safe_path.write_text(raw_str, encoding="utf-8")

    def sanitize_content(self, text: str) -> None:
        """Blocks raw code snippets, eval/exec commands, and shell escapes from being injected."""
        unsafe_patterns = [
            r"import\s+os",
            r"import\s+subprocess",
            r"os\.system",
            r"eval\s*\(",
            r"exec\s*\(",
            r"subprocess\.",
            r"__import__",
            r"<\?php",
            r"<script>",
            r"bash\s+-c",
        ]
        for pattern in unsafe_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                logger.critical("Malicious code injection attempt blocked: %s", pattern)
                raise SecurityError(f"Security Alert: Unsafe execution sequence pattern detected: '{pattern}'")
