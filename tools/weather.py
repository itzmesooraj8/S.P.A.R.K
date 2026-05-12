"""Weather via Open-Meteo with free geocoding."""

from __future__ import annotations

import logging
from typing import Any

import httpx

try:
    from geopy.geocoders import Nominatim
except Exception:  # pragma: no cover - optional dependency
    Nominatim = None

logger = logging.getLogger("SPARK_WEATHER")


def _geocode_with_open_meteo(location: str) -> dict[str, Any] | None:
    """Resolve a location using Open-Meteo's public geocoding API."""
    try:
        resp = httpx.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={
                "name": location,
                "count": 1,
                "language": "en",
                "format": "json",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results") if isinstance(data, dict) else None
        if not results:
            return None
        first = results[0]
        if not isinstance(first, dict):
            return None
        return {
            "latitude": first.get("latitude"),
            "longitude": first.get("longitude"),
            "name": first.get("name") or location,
            "admin1": first.get("admin1"),
            "country": first.get("country"),
        }
    except Exception as exc:
        logger.debug(f"Open-Meteo geocoding failed: {exc}")
        return None


def get_weather(location: str) -> dict:
    """Geocode a location and return current Open-Meteo weather data."""
    try:
        loc = None
        resolved_name = location

        if Nominatim is not None:
            try:
                geolocator = Nominatim(user_agent="spark-ai")
                loc = geolocator.geocode(location)
                if loc:
                    resolved_name = getattr(loc, "address", location) or location
            except Exception as exc:
                logger.debug(f"geopy geocoding failed: {exc}")

        if not loc:
            fallback = _geocode_with_open_meteo(location)
            if fallback:
                loc = fallback
                resolved_name = ", ".join(
                    part for part in [fallback.get("name"), fallback.get("admin1"), fallback.get("country")] if part
                ) or location

        if not loc:
            return {"error": f"Location not found: {location}"}

        latitude = getattr(loc, "latitude", None) if not isinstance(loc, dict) else loc.get("latitude")
        longitude = getattr(loc, "longitude", None) if not isinstance(loc, dict) else loc.get("longitude")
        if latitude is None or longitude is None:
            return {"error": f"Location not found: {location}"}

        resp = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
                "temperature_unit": "celsius",
            },
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        current = data["current"]
        return {
            "location": resolved_name,
            "temperature_c": current["temperature_2m"],
            "humidity_%": current["relative_humidity_2m"],
            "wind_kmh": current["wind_speed_10m"],
            "weather_code": current["weather_code"],
        }
    except Exception as exc:
        logger.error(f"Weather error: {exc}")
        return {"error": str(exc)}

