"""Weather via Open-Meteo with free geocoding."""

from __future__ import annotations

import logging

import httpx

try:
    from geopy.geocoders import Nominatim
except Exception:  # pragma: no cover - optional dependency
    Nominatim = None

logger = logging.getLogger("SPARK_WEATHER")


def get_weather(location: str) -> dict:
    """Geocode a location and return current Open-Meteo weather data."""
    try:
        if Nominatim is None:
            return {"error": "geopy is not installed"}

        geolocator = Nominatim(user_agent="spark-ai")
        loc = geolocator.geocode(location)
        if not loc:
            return {"error": f"Location not found: {location}"}

        resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "temperature_unit": "celsius",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        current = data["current"]
        return {
            "location": location,
            "temperature_c": current["temperature_2m"],
            "humidity_%": current["relative_humidity_2m"],
            "wind_kmh": current["wind_speed_10m"],
            "weather_code": current["weather_code"],
        }
    except Exception as exc:
        logger.error(f"Weather error: {exc}")
        return {"error": str(exc)}

