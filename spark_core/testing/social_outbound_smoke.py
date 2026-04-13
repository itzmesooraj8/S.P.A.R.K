"""
Smoke test for outbound social adapters.

This test does not require live Telegram/WhatsApp credentials.
Expected behavior without tokens: dispatcher returns status=skipped.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

CORE_DIR = Path(__file__).resolve().parents[1]
if str(CORE_DIR) not in sys.path:
    sys.path.insert(0, str(CORE_DIR))

from social.outbound import social_dispatcher


async def main():
    telegram_result = await social_dispatcher.dispatch(
        {
            "text": "smoke: telegram",
            "memory_session_id": "telegram:smoke-chat",
            "source": "telegram",
            "user_id": "telegram:smoke-chat",
        }
    )

    whatsapp_result = await social_dispatcher.dispatch(
        {
            "text": "smoke: whatsapp",
            "memory_session_id": "whatsapp:15550001111",
            "source": "whatsapp",
            "user_id": "whatsapp:15550001111",
            "metadata": {"phone_number_id": "1234567890"},
        }
    )

    sid = "telegram:smoke-route-fallback"
    await social_dispatcher.memory.save_message(
        sid,
        "user",
        "route seed",
        user_id="telegram:smoke-route-fallback",
        source="telegram",
        channel="social",
        platform_message_id="42",
        metadata={"chat_id": "smoke-route-fallback"},
    )
    fallback_result = await social_dispatcher.dispatch(
        {
            "text": "smoke: route fallback",
            "memory_session_id": sid,
            "source": "",
        }
    )

    print("telegram:", telegram_result)
    print("whatsapp:", whatsapp_result)
    print("fallback:", fallback_result)

    failures = []
    if telegram_result.get("status") not in {"sent", "skipped"}:
        failures.append("telegram result unexpected")
    if whatsapp_result.get("status") not in {"sent", "skipped"}:
        failures.append("whatsapp result unexpected")
    if fallback_result.get("status") not in {"sent", "skipped"}:
        failures.append("fallback result unexpected")

    if failures:
        raise SystemExit("; ".join(failures))


if __name__ == "__main__":
    asyncio.run(main())
