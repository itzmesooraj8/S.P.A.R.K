import urllib.request
import logging
import json

logger = logging.getLogger("SPARK_WEATHER")

def get_weather(location: str = "Palakkad") -> str:
    """Fetches a spoken weather briefing using wttr.in JSON API."""
    try:
        # wttr.in format=j1 provides rich JSON data
        encoded_loc = urllib.parse.quote(location)
        url = f"https://wttr.in/{encoded_loc}?format=j1"
        
        req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            
        current = data['current_condition'][0]
        temp = current['temp_C']
        feels_like = current['FeelsLikeC']
        desc = current['weatherDesc'][0]['value']
        humidity = current['humidity']
        
        briefing = f"It is currently {temp}°C and {desc.lower()} in {location}, sir."
        if abs(int(temp) - int(feels_like)) > 2:
            briefing += f" However, it feels more like {feels_like}°C."
        briefing += f" Humidity is at {humidity}%."
        
        return briefing
    except Exception as e:
        logger.error(f"Weather error: {e}")
        return f"I am unable to reach the meteorological satellites for {location} at this time, sir."

import urllib.parse
