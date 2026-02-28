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
# SIGNAL FUSION  — causal cross-source correlation engine
# ===========================================================================

import math
from typing import Any

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Return great-circle distance in km between two lat/lon points."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _severity_rank(s: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(s, 0)


async def _gather_fusion_data() -> dict[str, list]:
    """Concurrently fetch all data sources needed for fusion."""
    import asyncio

    async def _eq():
        try:
            d = await fetch_cached(
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
                ttl=300,
            )
            out = []
            for f in d.get("features", []):
                p = f.get("properties", {})
                g = f.get("geometry", {}).get("coordinates", [0, 0, 0])
                mag = p.get("mag", 0) or 0
                out.append({
                    "id": f.get("id", ""),
                    "type": "earthquake",
                    "title": p.get("place", "Unknown"),
                    "severity": "critical" if mag >= 7 else "high" if mag >= 6 else "medium" if mag >= 5 else "low",
                    "lat": g[1], "lon": g[0],
                    "ts": p.get("time", 0),
                    "meta": {"magnitude": mag, "depth_km": g[2] if len(g) > 2 else 0},
                })
            return out
        except Exception:
            return []

    async def _eonet():
        try:
            d = await fetch_cached(
                "https://eonet.gsfc.nasa.gov/api/v3/events",
                params={"status": "open", "days": 3, "limit": 60},
                ttl=300,
            )
            out = []
            CAT_SEV = {"Wildfires": "high", "Severe Storms": "high", "Volcanoes": "critical",
                       "Sea and Lake Ice": "medium", "Floods": "high", "Landslides": "medium",
                       "Drought": "medium", "Snow": "low", "Dust and Haze": "low"}
            for ev in d.get("events", []):
                cats = [c.get("title", "") for c in ev.get("categories", [])]
                cat = cats[0] if cats else "Natural"
                coords_list = []
                for g in ev.get("geometry", []):
                    c = g.get("coordinates", [])
                    if isinstance(c, list) and len(c) >= 2:
                        if isinstance(c[0], list):
                            for pt in c:
                                if len(pt) >= 2:
                                    coords_list.append((pt[1], pt[0]))
                        else:
                            coords_list.append((c[1], c[0]))
                if coords_list:
                    lat = sum(c[0] for c in coords_list) / len(coords_list)
                    lon = sum(c[1] for c in coords_list) / len(coords_list)
                    out.append({
                        "id": ev.get("id", ""),
                        "type": cat.lower().replace(" ", "_"),
                        "title": ev.get("title", cat),
                        "severity": CAT_SEV.get(cat, "medium"),
                        "lat": lat, "lon": lon,
                        "ts": 0,
                        "meta": {"category": cat},
                    })
            return out
        except Exception:
            return []

    async def _gdelt_conflict():
        try:
            d = await fetch_cached(
                "https://api.gdeltproject.org/api/v2/doc/doc",
                params={
                    "query": "conflict war explosion attack protest",
                    "mode": "artgeo",
                    "format": "json",
                    "maxrecords": "50",
                    "timespan": "24h",
                    "sort": "ToneDesc",
                },
                ttl=300,
            )
            out = []
            for a in d.get("articles", [])[:50]:
                lat = a.get("actiongeo_lat")
                lon = a.get("actiongeo_long")
                if lat and lon:
                    try:
                        lat, lon = float(lat), float(lon)
                    except (ValueError, TypeError):
                        continue
                    tone = float(a.get("tone", 0) or 0)
                    out.append({
                        "id": a.get("url", "")[:64],
                        "type": "conflict",
                        "title": a.get("title", "")[:120],
                        "severity": "critical" if tone < -10 else "high" if tone < -5 else "medium",
                        "lat": lat, "lon": lon,
                        "ts": 0,
                        "meta": {"tone": tone, "domain": a.get("domain", ""), "url": a.get("url", "")},
                    })
            return out
        except Exception:
            return []

    eqs, eonet, conflicts = await asyncio.gather(_eq(), _eonet(), _gdelt_conflict())
    return {"earthquake": eqs, "natural": eonet, "conflict": conflicts}


def _build_fusion_items(sources: dict[str, list]) -> list[dict[str, Any]]:
    """
    Cross-correlate events across sources within a 600 km spatial window.
    Returns up to 6 FusionItem dicts sorted by confidence descending.
    """
    all_events: list[dict] = []
    for evts in sources.values():
        all_events.extend(evts)

    if not all_events:
        return []

    # Cluster: build adjacency list of events within 600 km
    n = len(all_events)
    CLUSTER_KM = 600
    clusters: list[list[int]] = []
    visited = [False] * n

    for i in range(n):
        if visited[i]:
            continue
        cluster = [i]
        visited[i] = True
        for j in range(i + 1, n):
            if not visited[j]:
                dist = _haversine_km(
                    all_events[i]["lat"], all_events[i]["lon"],
                    all_events[j]["lat"], all_events[j]["lon"],
                )
                if dist <= CLUSTER_KM:
                    cluster.append(j)
                    visited[j] = True
        if len(cluster) >= 2:
            clusters.append(cluster)

    # Sort clusters by max severity rank * size
    def _cluster_score(cl: list[int]) -> float:
        ranks = [_severity_rank(all_events[i]["severity"]) for i in cl]
        types = {all_events[i]["type"] for i in cl}
        cross_bonus = 1.5 if len(types) > 1 else 1.0
        return max(ranks) * len(cl) * cross_bonus

    clusters.sort(key=_cluster_score, reverse=True)

    fusion_items: list[dict[str, Any]] = []
    CAUSE_EFFECT_PAIRS = {
        ("earthquake", "wildfire"):    ("ground rupture destabilizes terrain", "increased fire ignition risk"),
        ("earthquake", "conflict"):    ("infrastructure collapse", "civil unrest and resource conflict"),
        ("earthquake", "natural"):     ("seismic shaking", "secondary natural hazard triggered"),
        ("wildfire", "conflict"):      ("resource scarcity from fire damage", "population displacement tension"),
        ("wildfires", "conflict"):     ("resource scarcity from fire damage", "population displacement tension"),
        ("severe_storms", "conflict"): ("storm disrupts governance zones", "power vacuum exploitation risk"),
        ("conflict", "earthquake"):    ("conflict limits emergency response", "compounded disaster impact"),
        ("floods", "conflict"):        ("flood displaces civilian populations", "humanitarian access blocked"),
        ("volcanoes", "earthquake"):   ("volcanic stress transfer", "seismic cluster activation"),
    }

    for cl_idx, cl in enumerate(clusters[:6]):
        evts = [all_events[i] for i in cl]
        types = list({e["type"] for e in evts})
        # pick the two most severe events as cause/effect
        evts_sorted = sorted(evts, key=lambda e: _severity_rank(e["severity"]), reverse=True)
        cause_evt = evts_sorted[0]
        effect_evt = evts_sorted[1] if len(evts_sorted) > 1 else evts_sorted[0]

        # look up cause/effect description pair
        pair_key = (cause_evt["type"], effect_evt["type"])
        rev_key = (effect_evt["type"], cause_evt["type"])
        cause_desc, effect_desc = CAUSE_EFFECT_PAIRS.get(
            pair_key,
            CAUSE_EFFECT_PAIRS.get(
                rev_key,
                (f"{cause_evt['type'].replace('_',' ')} event", f"cascading impact on {effect_evt['type'].replace('_',' ')}"),
            ),
        )

        # confidence: more types + higher severity = higher confidence
        type_diversity = min(len(types) / 3.0, 1.0)
        max_sev_rank = max(_severity_rank(e["severity"]) for e in evts) / 4.0
        size_factor = min(len(evts) / 8.0, 1.0)
        confidence = round(0.4 * type_diversity + 0.35 * max_sev_rank + 0.25 * size_factor, 2)
        confidence = min(confidence, 0.97)

        # centroid
        clat = sum(e["lat"] for e in evts) / len(evts)
        clon = sum(e["lon"] for e in evts) / len(evts)

        # determine overall severity
        max_rank = max(_severity_rank(e["severity"]) for e in evts)
        severity = {4: "critical", 3: "high", 2: "medium", 1: "low"}.get(max_rank, "low")

        # entity extraction (locations from titles)
        entities: list[str] = []
        seen_ents: set[str] = set()
        for e in evts[:5]:
            words = e["title"].split()
            for w in words:
                if len(w) > 3 and w[0].isupper() and w not in seen_ents:
                    seen_ents.add(w)
                    entities.append(w)
                    if len(entities) >= 5:
                        break
            if len(entities) >= 5:
                break

        # data gaps
        all_types = {"earthquake", "conflict", "wildfire", "natural"}
        present_types = {e["type"] for e in evts}
        missing = all_types - present_types - {"natural"}  # broad catch
        data_gaps = [f"No {t} data in corridor" for t in list(missing)[:2]]
        if not data_gaps:
            data_gaps = ["Real-time satellite imagery pending"]

        # title generation
        type_label = " + ".join(t.replace("_", " ").title() for t in types[:2])
        region_hint = cause_evt["title"][:40].rstrip(",. ") if cause_evt["title"] else f"{clat:.1f}°, {clon:.1f}°"
        title = f"{type_label} Convergence — {region_hint}"

        # summary
        summary = (
            f"{len(evts)} correlated signal{'s' if len(evts) > 1 else ''} across "
            f"{len(types)} data stream{'s' if len(types) > 1 else ''} within a "
            f"{CLUSTER_KM} km corridor. Cross-source confidence: {int(confidence*100)}%. "
            f"Primary vector: {cause_evt['title'][:60]}."
        )

        fusion_items.append({
            "id": f"fusion-{cl_idx}-{int(time.time())}",
            "severity": severity,
            "confidence": confidence,
            "title": title,
            "summary": summary,
            "causeEvent": cause_desc,
            "effectEvent": effect_desc,
            "entities": entities,
            "dataGaps": data_gaps,
            "region": region_hint,
            "lat": clat,
            "lon": clon,
            "eventCount": len(evts),
            "sourceTypes": types,
            "timestamp": int(time.time() * 1000),
        })

    return fusion_items


@router.api_route("/api/globe/v1/getFusionSummary", methods=["POST", "GET", "OPTIONS"])
async def get_fusion_summary(request: Request):
    """
    Signal Fusion endpoint — cross-correlates earthquakes, natural disasters,
    and conflict signals within a 600 km spatial window to surface causal
    event clusters with confidence scores and cause→effect chains.
    """
    if request.method == "OPTIONS":
        return _options_response()
    try:
        sources = await _gather_fusion_data()
        items = _build_fusion_items(sources)
        return JSONResponse({
            "items": items,
            "generatedAt": int(time.time() * 1000),
            "sourceCounts": {k: len(v) for k, v in sources.items()},
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[Fusion] Error: {e}")
        return JSONResponse({"items": [], "generatedAt": int(time.time() * 1000), "sourceCounts": {}})


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

