"""Telegram Integration — Real Telegram bot using python-telegram-bot."""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("spark.integrations.telegram")


class TelegramIntegration:
    """Real Telegram bot integration."""

    def __init__(self, token: str | None = None) -> None:
        self._token = token or os.environ.get("TELEGRAM_TOKEN", "")
        self._bot = None
        self._connected = False
        self._message_handler = None

    async def connect(self) -> bool:
        if not self._token:
            logger.warning("Telegram token not set")
            return False
        try:
            from telegram import Update
            from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters

            self._app = ApplicationBuilder().token(self._token).build()

            async def handle_message(update: Update, context):
                if update.message and update.message.text:
                    if self._message_handler:
                        response = await self._message_handler(
                            update.message.text,
                            str(update.effective_user),
                            str(update.effective_chat.id),
                        )
                        await update.message.reply_text(response)

            async def start_command(update: Update, context):
                await update.message.reply_text("SPARK online. How can I help, sir?")

            self._app.add_handler(CommandHandler("start", start_command))
            self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

            self._connected = True
            logger.info("Telegram bot connected")
            return True
        except ImportError:
            logger.error("python-telegram-bot not installed: pip install python-telegram-bot")
            return False
        except Exception as exc:
            logger.error("Telegram connect failed: %s", exc)
            return False

    async def start(self) -> None:
        if self._app:
            import asyncio
            asyncio.create_task(self._app.run_polling())

    async def send(self, chat_id: int, message: str) -> dict[str, Any]:
        if not self._app:
            return {"success": False, "error": "Bot not connected"}
        try:
            await self._app.bot.send_message(chat_id=chat_id, text=message)
            return {"success": True, "chat_id": chat_id}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def on_message(self, handler) -> None:
        self._message_handler = handler

    async def disconnect(self) -> None:
        if self._app:
            await self._app.shutdown()
            self._connected = False

    def info(self) -> dict[str, Any]:
        return {"platform": "telegram", "connected": self._connected, "has_token": bool(self._token)}
