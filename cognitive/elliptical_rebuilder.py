from __future__ import annotations

import re

class EllipticalSentenceCompiler:
    def rebuild_command(self, raw_command: str, tool_logs: list[dict]) -> str:
        """Reconstructs incomplete/fragmented phrases into full instructions based on tool history."""
        cleaned = raw_command.lower().strip()
        if not tool_logs:
            return raw_command

        last_tool = tool_logs[-1]
        name = last_tool.get("tool", "")
        arg = last_tool.get("arg", "")

        if cleaned == "abort that" or cleaned == "stop it":
            return f"abort {name} execution immediately"

        if "the left one" in cleaned or "primary" in cleaned:
            if "monitor" in str(arg).lower() or "screen" in str(arg).lower():
                return "change display layout to primary monitor 1"

        return raw_command
