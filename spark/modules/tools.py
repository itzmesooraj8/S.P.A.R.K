import yfinance as yf
import json
import urllib.parse

def get_news_headlines(topic=None):
    """Returns the latest news headlines, optionally filtered by topic, using NewsAPI."""
    api_key = os.getenv("NEWSAPI_API_KEY")
    if not api_key:
        return "News API key not set."
    url = "https://newsapi.org/v2/top-headlines"
    params = {"apiKey": api_key, "language": "en"}
    if topic:
        params["q"] = topic
    try:
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("status") != "ok":
            return f"News error: {data.get('message', 'Unknown error')}"
        articles = data.get("articles", [])
        if not articles:
            return "No news found."
        headlines = [a["title"] for a in articles[:3]]
        return " | ".join(headlines)
    except Exception as e:
        return f"News error: {e}"

def get_stock_price(symbol):
    """Returns the latest stock price for the given symbol using Yahoo Finance."""
    try:
        stock = yf.Ticker(symbol)
        price = stock.info.get("regularMarketPrice")
        if price is not None:
            return f"{symbol.upper()} price: {price}"
        return f"No price found for {symbol.upper()}"
    except Exception as e:
        return f"Stock error: {e}"

def ask_wolframalpha(query):
    """Returns the answer to a query using WolframAlpha API."""
    appid = os.getenv("WOLFRAMALPHA_APP_ID")
    if not appid:
        return "WolframAlpha AppID not set."
    url = "http://api.wolframalpha.com/v1/result"
    params = {"i": query, "appid": appid}
    try:
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            return resp.text
        return f"WolframAlpha error: {resp.text}"
    except Exception as e:
        return f"WolframAlpha error: {e}"
import wikipediaapi
# --- Magic Toolbelt: Real-world tools for S.P.A.R.K. ---

def search_wikipedia(query, lang="en"):
    """Returns a summary for the given query from Wikipedia."""
    wiki = wikipediaapi.Wikipedia(language=lang, user_agent="SPARK/1.0 (https://github.com/your-repo)")
    page = wiki.page(query)
    if page.exists():
        # Return the first 2 sentences for brevity
        summary = page.summary.split('. ')
        return '. '.join(summary[:2]) + ('.' if len(summary) > 1 else '')
    else:
        return f"No Wikipedia article found for '{query}'."
import datetime
import requests
import os

# --- Magic Toolbelt: Real-world tools for S.P.A.R.K. ---

def get_current_time():
    """Returns the current local time as a formatted string."""
    now = datetime.datetime.now()
    return now.strftime('%I:%M %p on %A')

def get_current_weather(location="Kozhikode"):
    """Returns the current weather for the given location using OpenWeatherMap API."""
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Weather API key not set."
    url = f"https://api.openweathermap.org/data/2.5/weather?q={location}&appid={api_key}&units=metric"
    try:
        resp = requests.get(url)
        data = resp.json()
        if data.get("cod") != 200:
            return f"Weather unavailable: {data.get('message', 'Unknown error')}"
        desc = data['weather'][0]['description']
        temp = data['main']['temp']
        return f"{desc.capitalize()}, {temp}°C"
    except Exception as e:
        return f"Weather error: {e}"
