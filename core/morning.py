import logging
from tools.sysmon import get_system_health
from tools.weather import get_weather
from tools.web_search import get_indian_market_summary

logger = logging.getLogger("SPARK_MORNING")


def _format_weather_summary(weather: dict) -> str | None:
    if not weather:
        return None
    if "error" in weather:
        return None

    location = weather.get("location", "your area")
    temperature = weather.get("temperature_c")
    humidity = weather.get("humidity_%")
    wind = weather.get("wind_kmh")

    details = []
    if temperature is not None:
        details.append(f"{temperature}°C")
    if humidity is not None:
        details.append(f"humidity {humidity}%")
    if wind is not None:
        details.append(f"wind {wind} km/h")

    if not details:
        return f"Weather for {location} is available."
    return f"Weather for {location}: " + ", ".join(details) + "."

def generate_morning_briefing() -> str:
    """
    Generates a J.A.R.V.I.S.-style morning briefing.
    Combines System Health, Weather, and Market performance into a single cohesive monologue.
    """
    logger.info("Generating morning briefing...")
    briefing_parts = []
    
    # 1. Greeting & System Health
    sys_health = get_system_health()
    # Clean up the status for speech flow
    if "nominal" in sys_health:
        sys_health = "All systems are nominal."
    briefing_parts.append(f"Good morning, sir. {sys_health}")
    
    # 2. Weather
    weather = get_weather("Palakkad")
    weather_summary = _format_weather_summary(weather)
    if weather_summary:
        briefing_parts.append(weather_summary)
        
    # 3. Markets
    markets = get_indian_market_summary()
    if markets:
        briefing_parts.append(f"On the markets, {markets}")
        
    briefing_parts.append("Ready for your commands for the day.")
    
    return " ".join(briefing_parts)
