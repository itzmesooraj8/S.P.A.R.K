from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

log = logging.getLogger("spark.mcp")

ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "config" / "mcp_servers.json"


@dataclass(slots=True)
class MCPServerConfig:
    name: str
    command: str
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    cwd: str | None = None


class MCPManager:
    def __init__(self, config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
        self.config_path = Path(config_path)
        self._servers: list[MCPServerConfig] = []
        self._tool_index: dict[str, str] = {}
        self._tool_cache: list[dict[str, Any]] = []
        self._loaded = False

    def _load_config(self) -> list[MCPServerConfig]:
        if not self.config_path.exists():
            return []

        try:
            raw = json.loads(self.config_path.read_text(encoding="utf-8"))
        except Exception as exc:
            log.warning("MCP config could not be read: %s", exc)
            return []

        servers: list[MCPServerConfig] = []
        for entry in raw.get("servers", []) if isinstance(raw, dict) else []:
            if not isinstance(entry, dict) or not entry.get("enabled", True):
                continue
            command = str(entry.get("command", "")).strip()
            if not command:
                continue
            servers.append(
                MCPServerConfig(
                    name=str(entry.get("name", command)).strip() or command,
                    command=command,
                    args=[str(arg) for arg in entry.get("args", []) if str(arg).strip()],
                    env={str(key): str(value) for key, value in dict(entry.get("env", {})).items()},
                    cwd=str(entry.get("cwd")) if entry.get("cwd") else None,
                )
            )
        return servers

    async def _query_server_tools(self, server: MCPServerConfig) -> list[dict[str, Any]]:
        params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=server.env or None,
            cwd=server.cwd,
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.list_tools()

        normalized: list[dict[str, Any]] = []
        for tool in result.tools:
            normalized.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description or f"MCP tool from {server.name}",
                        "parameters": tool.inputSchema or {"type": "object", "properties": {}},
                    },
                }
            )
            self._tool_index[tool.name] = server.name
        return normalized

    async def refresh(self) -> list[dict[str, Any]]:
        self._servers = self._load_config()
        self._tool_index.clear()
        self._tool_cache = []
        for server in self._servers:
            try:
                self._tool_cache.extend(await self._query_server_tools(server))
            except Exception as exc:
                log.info("MCP server '%s' unavailable: %s", server.name, exc)
        self._loaded = True
        return list(self._tool_cache)

    async def list_tool_specs(self) -> list[dict[str, Any]]:
        if not self._loaded:
            return await self.refresh()
        return list(self._tool_cache)

    async def has_tool(self, tool_name: str) -> bool:
        if not self._loaded:
            await self.refresh()
        return tool_name in self._tool_index

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        if not self._loaded:
            await self.refresh()

        server_name = self._tool_index.get(tool_name)
        if not server_name:
            raise KeyError(f"Unknown MCP tool: {tool_name}")

        server = next((entry for entry in self._servers if entry.name == server_name), None)
        if server is None:
            raise KeyError(f"MCP server not configured for tool: {tool_name}")

        params = StdioServerParameters(
            command=server.command,
            args=server.args,
            env=server.env or None,
            cwd=server.cwd,
        )
        async with stdio_client(params) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments or {})

        if result.structuredContent is not None:
            return result.structuredContent

        content_parts: list[str] = []
        for item in result.content:
            text = getattr(item, "text", None)
            if text:
                content_parts.append(str(text))
                continue
            data = getattr(item, "data", None)
            if data is not None:
                try:
                    content_parts.append(json.dumps(data, ensure_ascii=False))
                except Exception:
                    content_parts.append(str(data))
                continue
            content_parts.append(str(item))

        return "\n".join(content_parts).strip() or json.dumps(result.model_dump(), ensure_ascii=False)