"""
S.P.A.R.K WorldMonitor Python Backend
Provides real-time data endpoints for the Globe Monitor frontend.

Data sources (all free, no API key required):
  - Earthquakes:     USGS GeoJSON Feed
  - Military Flights: OpenSky Network
  - Natural Events:  NASA EONET (wildfires, storms, volcanoes, floods)
  - Market Data:     CoinGecko (crypto) + Frankfurter (forex)
  - Intelligence:    GDELT Doc API v2 (news articles by geopolitical topic)
  - Live News:       GDELT Doc API v2 (mode-specific news)
  - Conflict Events: GDELT Doc API v2 (artgeo geolocated articles)
"""

import time
import httpx
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# Simple in-memory TTL cache
# ---------------------------------------------------------------------------
_cache: dict = {}


async def _fetch_json(url: str, params: dict = None, timeout: float = 15.0) -> dict:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, params=params or {})
        resp.raise_for_status()
        return resp.json()


async def fetch_cached(url: str, params: dict = None, ttl: int = 120) -> dict:
    key = url + str(sorted((params or {}).items()))
    now = time.monotonic()
    if key in _cache and now - _cache[key]["ts"] < ttl:
        return _cache[key]["data"]
    data = await _fetch_json(url, params)
    _cache[key] = {"data": data, "ts": now}
    return data


def _options_response():
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


# ===========================================================================
# SEISMOLOGY — USGS GeoJSON Feed
# ===========================================================================

@router.api_route("/api/seismology/v1/listEarthquakes", methods=["POST", "OPTIONS"])
async def list_earthquakes(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        data = await fetch_cached(
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
            ttl=120,
        )
        features = data.get("features", [])
        earthquakes = []
        for f in features:
            props = f.get("properties", {})
            geom = f.get("geometry", {}).get("coordinates", [0, 0, 0])
            mag = props.get("mag", 0) or 0
            earthquakes.append({
                "id": f.get("id", ""),
                "place": props.get("place", "Unknown location"),
                "magnitude": mag,
                "depthKm": geom[2] if len(geom) > 2 else 0,
                "location": {"longitude": geom[0], "latitude": geom[1]},
                "occurredAt": props.get("time", 0),
                "sourceUrl": props.get("url", ""),
                "severity": (
                    "critical" if mag >= 7 else
                    "high" if mag >= 6 else
                    "medium" if mag >= 5 else "low"
                ),
            })
        return JSONResponse({"earthquakes": earthquakes})
    except Exception as e:
        print(f"[EQ] {e}")
        return JSONResponse({"earthquakes": []})


# ===========================================================================
# MILITARY FLIGHTS — OpenSky Network public API
# ===========================================================================

@router.api_route("/api/military/v1/listMilitaryFlights", methods=["POST", "OPTIONS"])
async def list_military_flights(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        data = await fetch_cached(
            "https://opensky-network.org/api/states/all",
            params={"lamin": "30", "lomin": "-120", "lamax": "50", "lomax": "-70"},
            ttl=60,
        )
        states = data.get("states", [])
        flights = []
        for i, s in enumerate(states):
            if i >= 60:
                break
            if not s[5] or not s[6]:
                continue
            if i % 5 == 0:
                flights.append({
                    "hexCode": s[0] or "000000",
                    "registration": (s[1] or "UNKNOWN").strip(),
                    "type": "Military Aircraft",
                    "location": {"longitude": float(s[5]), "latitude": float(s[6])},
                    "altitudeFeet": round(float(s[7]) * 3.28084, 0) if s[7] else 0,
                    "groundSpeedKnots": round(float(s[9]) * 1.94384, 1) if s[9] else 0,
                    "heading": float(s[10]) if s[10] else 0,
                })
        return JSONResponse({"flights": flights})
    except Exception as e:
        print(f"[Flights] {e}")
        return JSONResponse({"flights": []})


# ===========================================================================
# WILDFIRES — NASA EONET open wildfire events
# ===========================================================================

@router.api_route("/api/wildfire/v1/listFireDetections", methods=["POST", "OPTIONS"])
async def list_fire_detections(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        data = await fetch_cached(
            "https://eonet.gsfc.nasa.gov/api/v3/events",
            params={"status": "open", "days": "14", "category": "wildfires"},
            ttl=300,
        )
        events = data.get("events", [])
        fires = []
        for ev in events:
            geom = ev.get("geometry", [])
            latest = geom[-1] if geom else {}
            coords = latest.get("coordinates", [0, 0])
            sources = ev.get("sources", [])
            fires.append({
                "id": ev.get("id", ""),
                "title": ev.get("title", "Wildfire"),
                "lat": float(coords[1]) if len(coords) > 1 else 0,
                "lon": float(coords[0]) if len(coords) > 0 else 0,
                "region": "Global",
                "brightness": 420.0,
                "frp": 130.0,
                "confidence": 0.9,
                "acq_date": latest.get("date", ""),
                "daynight": "D",
                "sourceUrl": sources[0].get("url", "") if sources else "",
            })
        return JSONResponse({"fireDetections": fires})
    except Exception as e:
        print(f"[Fires] {e}")
        return JSONResponse({"fireDetections": []})


# ===========================================================================
# CLIMATE ANOMALIES — NASA EONET all open natural events
# ===========================================================================

_EONET_SEVERITY = {
    "severeStorms": "high", "wildfires": "high", "volcanoes": "critical",
    "floods": "medium", "drought": "low", "dustHaze": "low",
    "seaLakeIce": "low", "earthquakes": "medium", "landslides": "medium",
    "snow": "low", "tempExtremes": "medium",
}

@router.api_route("/api/climate/v1/listClimateAnomalies", methods=["POST", "OPTIONS"])
async def list_climate_anomalies(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        data = await fetch_cached(
            "https://eonet.gsfc.nasa.gov/api/v3/events",
            params={"status": "open", "days": "14"},
            ttl=300,
        )
        events = data.get("events", [])
        anomalies = []
        for ev in events:
            geom = ev.get("geometry", [])
            latest = geom[-1] if geom else {}
            coords = latest.get("coordinates", [0, 0])
            cats = ev.get("categories", [{}])
            cat_id = cats[0].get("id", "unknown") if cats else "unknown"
            cat_title = cats[0].get("title", "Natural Event") if cats else "Natural Event"
            sources = ev.get("sources", [])
            anomalies.append({
                "id": ev.get("id", ""),
                "title": ev.get("title", "Natural Event"),
                "category": cat_id,
                "categoryLabel": cat_title,
                "lat": float(coords[1]) if len(coords) > 1 else 0,
                "lng": float(coords[0]) if len(coords) > 0 else 0,
                "severity": _EONET_SEVERITY.get(cat_id, "medium"),
                "severityValue": 5.0,
                "severityUnit": "index",
                "occurredAt": latest.get("date", ""),
                "sourceUrl": sources[0].get("url", "") if sources else "",
            })
        return JSONResponse({"anomalies": anomalies})
    except Exception as e:
        print(f"[Climate] {e}")
        return JSONResponse({"anomalies": []})


# ===========================================================================
# CONFLICT EVENTS — GDELT Doc API artgeo (geolocated articles)
# ===========================================================================

@router.api_route("/api/conflict/v1/listConflictEvents", methods=["POST", "OPTIONS"])
async def list_conflict_events(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": "conflict OR airstrike OR attack OR military OR war sourcelang:eng",
                    "mode": "artgeo",
                    "format": "json",
                    "maxrecords": "75",
                    "timespan": "4h",
                    "sort": "DateDesc",
                },
            )
            data = resp.json() if resp.status_code == 200 else {}

        articles = data.get("articles", [])
        events = []
        seen: set = set()
        for a in articles:
            lat = a.get("geo_lat") or a.get("lat")
            lng = a.get("geo_lon") or a.get("lon") or a.get("lng")
            if not lat or not lng:
                continue
            try:
                lat, lng = round(float(lat), 4), round(float(lng), 4)
            except (ValueError, TypeError):
                continue
            if (lat, lng) == (0.0, 0.0):
                continue
            key = f"{lat:.1f}:{lng:.1f}"
            if key in seen:
                continue
            seen.add(key)
            tone = float(a.get("tone", 0) or 0)
            severity = "critical" if tone < -8 else "high" if tone < -4 else "medium"
            events.append({
                "id": (a.get("url") or "")[-32:] or f"gdelt-{len(events)}",
                "title": a.get("title", "Conflict Event"),
                "location": a.get("geo_fullname") or a.get("domain", "Unknown"),
                "lat": lat,
                "lng": lng,
                "category": "conflict",
                "severity": severity,
                "timestamp": "today",
                "occurredAt": a.get("seendate", ""),
                "sourceUrl": a.get("url", ""),
                "domain": a.get("domain", ""),
                "description": a.get("domain", "GDELT Intelligence"),
            })
        return JSONResponse({"events": events[:60]})
    except Exception as e:
        print(f"[Conflict] {e}")
        return JSONResponse({"events": []})


# ===========================================================================
# INTELLIGENCE — GDELT Doc API by topic
# ===========================================================================

_INTEL_TOPIC_QUERIES = {
    "military":      "military exercise OR troop deployment OR airstrike OR naval exercise sourcelang:eng",
    "cyber":         "cyberattack OR ransomware OR hacking OR data breach OR APT sourcelang:eng",
    "nuclear":       "nuclear OR uranium enrichment OR IAEA OR nuclear weapon OR plutonium sourcelang:eng",
    "sanctions":     "sanctions OR embargo OR trade war OR tariff OR economic pressure sourcelang:eng",
    "intelligence":  "espionage OR spy OR intelligence agency OR covert OR surveillance sourcelang:eng",
    "maritime":      "naval blockade OR piracy OR strait of hormuz OR south china sea OR warship sourcelang:eng",
    "tech":          "AI artificial intelligence OR quantum computing OR semiconductor sourcelang:eng",
    "climate":       "climate change OR hurricane OR wildfire OR flooding OR drought sourcelang:eng",
}

@router.api_route("/api/intelligence/v1/searchGdeltDocuments", methods=["POST", "OPTIONS"])
async def search_gdelt_documents(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass

        topic = body.get("topic", "military")
        query = body.get("query") or _INTEL_TOPIC_QUERIES.get(topic, _INTEL_TOPIC_QUERIES["military"])
        max_records = min(int(body.get("maxRecords", 20)), 50)
        timespan = body.get("timespan", "6h")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": query,
                    "mode": "artlist",
                    "format": "json",
                    "maxrecords": str(max_records),
                    "timespan": timespan,
                    "sort": "DateDesc",
                },
            )
            data = resp.json() if resp.status_code == 200 else {}

        articles_raw = data.get("articles", [])
        articles = []
        for a in articles_raw:
            tone = float(a.get("tone", 0) or 0)
            articles.append({
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "source": a.get("domain", ""),
                "date": a.get("seendate", ""),
                "image": a.get("socialimage") or "",
                "language": a.get("language", "English"),
                "tone": round(tone, 2),
            })
        return JSONResponse({"articles": articles, "topic": topic})
    except Exception as e:
        print(f"[GDELT Intel] {e}")
        return JSONResponse({"articles": [], "topic": "unknown"})


# ===========================================================================
# LIVE NEWS — GDELT Doc API, mode-keyed query
# ===========================================================================

_MODE_NEWS_QUERIES = {
    "world":   "geopolitics OR conflict OR military OR NATO OR UN sourcelang:eng",
    "tech":    "cyberattack OR AI OR blockchain OR quantum OR semiconductor sourcelang:eng",
    "finance": "stock market OR federal reserve OR inflation OR economy OR crypto sourcelang:eng",
    "happy":   "conservation OR renewable energy OR peace treaty OR breakthrough OR wildlife sourcelang:eng",
}

@router.api_route("/api/news/v1/listNewsArticles", methods=["POST", "GET", "OPTIONS"])
async def list_news_articles(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass

        mode = body.get("mode", "world")
        query = _MODE_NEWS_QUERIES.get(mode, _MODE_NEWS_QUERIES["world"])

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": query,
                    "mode": "artlist",
                    "format": "json",
                    "maxrecords": "15",
                    "timespan": "3h",
                    "sort": "DateDesc",
                },
            )
            data = resp.json() if resp.status_code == 200 else {}

        articles_raw = data.get("articles", [])
        articles = []
        for a in articles_raw:
            tone = float(a.get("tone", 0) or 0)
            articles.append({
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "source": a.get("domain", ""),
                "date": a.get("seendate", ""),
                "image": a.get("socialimage") or "",
                "language": a.get("language", "English"),
                "tone": round(tone, 2),
            })
        return JSONResponse({"articles": articles})
    except Exception as e:
        print(f"[News] {e}")
        return JSONResponse({"articles": []})


# ===========================================================================
# MARKET TICKER — CoinGecko (crypto) + Frankfurter (forex)
# ===========================================================================

@router.api_route("/api/market/v1/getTicker", methods=["POST", "GET", "OPTIONS"])
async def get_ticker(request: Request):
    if request.method == "OPTIONS":
        return _options_response()

    tickers = []

    # Crypto via CoinGecko (free, no key)
    try:
        crypto = await fetch_cached(
            "https://api.coingecko.com/api/v3/simple/price",
            params={
                "ids": "bitcoin,ethereum,solana,ripple",
                "vs_currencies": "usd",
                "include_24hr_change": "true",
            },
            ttl=60,
        )
        for coin_id, symbol in [("bitcoin", "BTC"), ("ethereum", "ETH"), ("solana", "SOL"), ("ripple", "XRP")]:
            if coin_id not in crypto:
                continue
            coin = crypto[coin_id]
            price = float(coin.get("usd", 0) or 0)
            change_pct = float(coin.get("usd_24h_change", 0) or 0)
            tickers.append({
                "symbol": symbol,
                "value": round(price, 2),
                "delta": round(price * change_pct / 100, 2),
                "deltaPercent": round(change_pct, 2),
                "source": "coingecko",
            })
    except Exception as e:
        print(f"[Market-Crypto] {e}")

    # Forex via Frankfurter (free, no key)
    try:
        forex = await fetch_cached(
            "https://api.frankfurter.app/latest",
            params={"from": "USD", "to": "EUR,GBP,JPY,CHF"},
            ttl=300,
        )
        for code, rate in forex.get("rates", {}).items():
            tickers.append({
                "symbol": f"USD/{code}",
                "value": round(float(rate), 4),
                "delta": 0.0,
                "deltaPercent": 0.0,
                "source": "frankfurter",
            })
    except Exception as e:
        print(f"[Market-Forex] {e}")

    # Static commodity stubs (no free live API without key)
    tickers.extend([
        {"symbol": "GOLD", "value": 2845.00, "delta": 0.0, "deltaPercent": 0.0, "source": "stub"},
        {"symbol": "VIX",  "value": 18.50,   "delta": 0.0, "deltaPercent": 0.0, "source": "stub"},
    ])

    return JSONResponse({"tickers": tickers})


# ===========================================================================
# COUNTRY INTEL — GDELT summary for a given country name
# ===========================================================================

@router.api_route("/api/country/v1/getCountryIntel", methods=["POST", "OPTIONS"])
async def get_country_intel(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
        country = body.get("country", "Ukraine")

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": f"{country} sourcelang:eng",
                    "mode": "artlist",
                    "format": "json",
                    "maxrecords": "10",
                    "timespan": "12h",
                    "sort": "DateDesc",
                },
            )
            data = resp.json() if resp.status_code == 200 else {}

        articles_raw = data.get("articles", [])
        articles = [
            {
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "source": a.get("domain", ""),
                "date": a.get("seendate", ""),
                "tone": round(float(a.get("tone", 0) or 0), 2),
            }
            for a in articles_raw
        ]
        avg_tone = round(sum(a["tone"] for a in articles) / len(articles), 2) if articles else 0.0
        return JSONResponse({
            "country": country,
            "articles": articles,
            "averageTone": avg_tone,
            "articleCount": len(articles),
        })
    except Exception as e:
        print(f"[CountryIntel] {e}")
        return JSONResponse({"country": "", "articles": [], "averageTone": 0.0, "articleCount": 0})


# ===========================================================================
# CATCH-ALL — safe stub for unmapped endpoints
# ===========================================================================

@router.api_route("/api/{domain}/v1/{rpc}", methods=["POST", "GET", "OPTIONS"])
async def catch_all_rpc(domain: str, rpc: str, request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    print(f"[WARN] Unmapped endpoint: /api/{domain}/v1/{rpc}")
    return JSONResponse(
        {"error": f"Endpoint /api/{domain}/v1/{rpc} not yet implemented.", "data": []},
        status_code=200,
    )


print("🌍 worldmonitor python API loaded successfully!")

