import logging
from tools.sysmon import get_system_health
from tools.weather import get_weather
from tools.web_search import get_indian_market_summary

logger = logging.getLogger("SPARK_MORNING")

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
    if weather and "unable" not in weather:
        # Strip "sir" from weather to avoid repetition
        weather = weather.replace(", sir", "")
        briefing_parts.append(weather)
        
    # 3. Markets
    markets = get_indian_market_summary()
    if markets:
        briefing_parts.append(f"On the markets, {markets}")
        
    briefing_parts.append("Ready for your commands for the day.")
    
    return " ".join(briefing_parts)
