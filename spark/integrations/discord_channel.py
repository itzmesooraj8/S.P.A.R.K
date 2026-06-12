"""Discord Integration — Real Discord bot using discord.py."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("spark.integrations.discord")


class DiscordIntegration:
    """Real Discord bot integration using discord.py."""

    def __init__(self, token: str | None = None) -> None:
        self._token = token or os.environ.get("DISCORD_TOKEN", "")
        self._bot = None
        self._connected = False
        self._message_handler = None

    async def connect(self) -> bool:
        if not self._token:
            logger.warning("Discord token not set")
            return False
        try:
            import discord
            from discord.ext import commands

            intents = discord.Intents.default()
            intents.message_content = True
            self._bot = commands.Bot(command_prefix="!", intents=intents)

            @self._bot.event
            async def on_ready():
                self._connected = True
                logger.info("Discord bot connected as %s", self._bot.user)

            @self._bot.event
            async def on_message(message):
                if message.author == self._bot.user:
                    return
                if self._message_handler:
                    await self._message_handler(message.content, str(message.author), str(message.channel))

            @self._bot.command(name="spark")
            async def spark_command(ctx, *, text: str):
                if self._message_handler:
                    response = await self._message_handler(text, str(ctx.author), str(ctx.channel))
                    await ctx.send(response)

            return True
        except ImportError:
            logger.error("discord.py not installed: pip install discord.py")
            return False
        except Exception as exc:
            logger.error("Discord connect failed: %s", exc)
            return False

    async def start(self) -> None:
        if self._bot and self._token:
            import asyncio
            asyncio.create_task(self._bot.start(self._token))

    async def send(self, channel_id: int, message: str) -> dict[str, Any]:
        if not self._bot:
            return {"success": False, "error": "Bot not connected"}
        try:
            channel = self._bot.get_channel(channel_id)
            if channel:
                await channel.send(message)
                return {"success": True, "channel_id": channel_id}
            return {"success": False, "error": "Channel not found"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def on_message(self, handler) -> None:
        self._message_handler = handler

    async def disconnect(self) -> None:
        if self._bot:
            await self._bot.close()
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def info(self) -> dict[str, Any]:
        return {"platform": "discord", "connected": self._connected, "has_token": bool(self._token)}
