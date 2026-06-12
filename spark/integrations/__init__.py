"""
Spark Integrations — Real Communication Channels

- Discord (discord.py)
- Email (SMTP)
- Telegram (python-telegram-bot)
"""

from spark.integrations.discord_channel import DiscordIntegration
from spark.integrations.email_channel import EmailIntegration
from spark.integrations.telegram_channel import TelegramIntegration

__all__ = ["DiscordIntegration", "EmailIntegration", "TelegramIntegration"]
