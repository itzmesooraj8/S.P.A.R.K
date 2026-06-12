"""Email Integration — Real SMTP email sending and IMAP reading."""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Any

logger = logging.getLogger("spark.integrations.email")


class EmailIntegration:
    """Real email integration using SMTP/IMAP."""

    def __init__(self, smtp_host: str | None = None, smtp_port: int = 587, username: str | None = None, password: str | None = None) -> None:
        self._smtp_host = smtp_host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
        self._smtp_port = smtp_port
        self._username = username or os.environ.get("SMTP_USERNAME", "")
        self._password = password or os.environ.get("SMTP_PASSWORD", "")
        self._connected = False

    async def connect(self) -> bool:
        if not self._username or not self._password:
            logger.warning("Email credentials not set")
            return False
        try:
            server = smtplib.SMTP(self._smtp_host, self._smtp_port)
            server.starttls()
            server.login(self._username, self._password)
            server.quit()
            self._connected = True
            logger.info("Email connected to %s", self._smtp_host)
            return True
        except Exception as exc:
            logger.error("Email connect failed: %s", exc)
            return False

    async def send(self, to: str, subject: str, body: str, html: bool = False) -> dict[str, Any]:
        if not self._connected:
            return {"success": False, "error": "Not connected"}
        try:
            msg = MIMEMultipart()
            msg["From"] = self._username
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "html" if html else "plain"))

            server = smtplib.SMTP(self._smtp_host, self._smtp_port)
            server.starttls()
            server.login(self._username, self._password)
            server.send_message(msg)
            server.quit()

            logger.info("Email sent to %s: %s", to, subject)
            return {"success": True, "to": to, "subject": subject}
        except Exception as exc:
            logger.error("Email send failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def disconnect(self) -> None:
        self._connected = False

    def info(self) -> dict[str, Any]:
        return {"platform": "email", "connected": self._connected, "host": self._smtp_host}
