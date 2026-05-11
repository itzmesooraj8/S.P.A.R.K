"""High-level home scenes triggered by voice."""

from __future__ import annotations

import asyncio

from tools.iot import control_device
from tools.voice import speak


async def scene_leaving():
    for device in ["fan", "light", "bedroom_light", "ac"]:
        control_device(device, "off")
    await speak("All devices off. Home secured. Safe travels.")
    return "Leaving home - all devices off."


async def scene_arriving(eta_minutes: int = 10):
    control_device("ac", "on")
    await speak("Got it. AC on. I'll have everything ready when you arrive.")
    await asyncio.sleep(eta_minutes * 60)
    control_device("light", "on")
    control_device("fan", "on")
    return "Home ready for arrival."


async def scene_good_night():
    control_device("light", "off")
    control_device("bedroom_light", "off")
    control_device("ac", "off")
    control_device("fan", "on")
    await speak("Good night.")
    return "Good night scene activated."
