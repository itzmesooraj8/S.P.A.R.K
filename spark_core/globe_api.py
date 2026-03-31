"""
S.P.A.R.K Globe Intelligence API
Serves real-time geospatial data for the Globe Monitor HUD.

Architecture:
  - Per-provider circuit breakers (3 failures → 60s cooldown)
  - Provider health endpoint (/api/globe/v1/getProviderHealth)
  - Layer-aware loading (disabled layers skip their fetch + interval)
  - Optional API key support (ACLED, FINNHUB, EIA, NASA_FIRMS, CLOUDFLARE, OPENSKY)
  - Explicit degraded-mode responses (no silent {} failures)
  - Server-side TTL cache with per-provider TTL tuning

Data sources:
  Free (no key):
    USGS Earthquake Feed · OpenSky Network · NASA EONET
    CoinGecko / Frankfurter · GDELT Doc API v2
  Optional (keyed, features unlocked):
    ACLED_ACCESS_TOKEN       → enriched conflict locations
    FINNHUB_API_KEY          → stock & forex quotes
    EIA_API_KEY              → US energy prices
    NASA_FIRMS_API_KEY       → FIRMS fire detections (vs EONET fallback)
    CLOUDFLARE_API_TOKEN     → internet outage layer
    OPENSKY_CLIENT_ID/SECRET → higher OpenSky rate limits
"""

from __future__ import annotations

import asyncio
import math
import os
import time
import xml.etree.ElementTree as ET
from typing import Any
from pathlib import Path

import httpx
import yaml
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

router = APIRouter()

# ──────────────────────────────────────────────────────────────
# Optional API keys — env vars take priority, secrets.yaml fallback
# ──────────────────────────────────────────────────────────────
def _load_secrets_yaml() -> dict:
    """Load secrets.yaml from project root (two levels up from this file)."""
    try:
        root = Path(__file__).parent.parent
        p = root / "config" / "secrets.yaml"
        if p.exists():
            data = yaml.safe_load(p.read_text()) or {}
            return data.get("keys", {})
    except Exception:
        pass
    return {}

_YAML_KEYS = _load_secrets_yaml()

def _key(env_name: str, yaml_name: str) -> str | None:
    """Return env var if set, else secrets.yaml value, else None."""
    val = os.getenv(env_name) or _YAML_KEYS.get(yaml_name, "") or None
    return val if val and val.strip() else None

_KEYS = {
    "acled":       _key("ACLED_ACCESS_TOKEN",   "acled_access_token"),
    "acled_email": _key("ACLED_EMAIL",           "acled_email"),
    "finnhub":     _key("FINNHUB_API_KEY",       "finnhub_api_key"),
    "eia":         _key("EIA_API_KEY",           "eia_api_key"),
    "nasa_firms":  _key("NASA_FIRMS_API_KEY",    "nasa_firms_api_key"),
    "newsdata":    _key("NEWSDATA_API_KEY",      "newsdata_api_key"),
    "cloudflare":  _key("CLOUDFLARE_API_TOKEN",  "cloudflare_api_token"),
    "opensky_id":  _key("OPENSKY_CLIENT_ID",     "opensky_client_id"),
    "opensky_sec": _key("OPENSKY_CLIENT_SECRET", "opensky_client_secret"),
}


# ──────────────────────────────────────────────────────────────
# Circuit breaker
# ──────────────────────────────────────────────────────────────
class CircuitBreaker:
    THRESHOLD = 3      # failures before open
    COOLDOWN  = 60.0   # seconds to stay open

    def __init__(self, name: str):
        self.name            = name
        self.failure_count   = 0
        self.cooldown_until  = 0.0
        self.last_ok         = 0.0
        self.last_error      = ""
        self.status          = "ok"  # ok | degraded | down | key_required

    # ── query ──────────────────────────────────────────────────
    def is_open(self) -> bool:
        """True = skip the call (circuit open)."""
        if self.status == "key_required":
            return True
        if self.failure_count >= self.THRESHOLD:
            if time.monotonic() < self.cooldown_until:
                return True
            # cooldown expired, allow one probe
            self.failure_count = self.THRESHOLD - 1
        return False

    # ── record outcomes ────────────────────────────────────────
    def success(self) -> None:
        self.failure_count  = 0
        self.last_ok        = time.monotonic()
        self.last_error     = ""
        self.status         = "ok"

    def failure(self, err: str) -> None:
        self.failure_count += 1
        self.last_error     = str(err)[:240]
        now = time.monotonic()
        if self.failure_count >= self.THRESHOLD:
            self.cooldown_until = now + self.COOLDOWN
            self.status         = "down"
        else:
            self.status = "degraded"

    def set_key_required(self) -> None:
        self.status = "key_required"

    # ── serialise ──────────────────────────────────────────────
    def to_dict(self) -> dict:
        now = time.monotonic()
        return {
            "name":              self.name,
            "status":            self.status,
            "failureCount":      self.failure_count,
            "lastOkAgo":         int(now - self.last_ok) if self.last_ok else None,
            "lastError":         self.last_error,
            "cooldownRemaining": max(0, int(self.cooldown_until - now))
                                 if self.failure_count >= self.THRESHOLD else 0,
        }


# ── Register all providers ─────────────────────────────────────
_CB: dict[str, CircuitBreaker] = {
    name: CircuitBreaker(name) for name in [
        # Free providers
        "usgs", "waqi", "newsdata"
    ]
}

# Source metadata for provenance stamping
_PROVIDER_META: dict[str, dict] = {
    "usgs":         {"name": "USGS GeoJSON Feed",       "url": "https://earthquake.usgs.gov/"},
    "opensky":      {"name": "OpenSky Network",          "url": "https://opensky-network.org/"},
    "eonet":        {"name": "NASA EONET",               "url": "https://eonet.gsfc.nasa.gov/"},
    "gdelt_conflict":{"name": "GDELT Document API v2",  "url": "https://api.gdeltproject.org/"},
    "gdelt_intel":  {"name": "GDELT Document API v2",   "url": "https://api.gdeltproject.org/"},
    "gdelt_news":   {"name": "GDELT Document API v2",   "url": "https://api.gdeltproject.org/"},
    "coingecko":    {"name": "CoinGecko API",            "url": "https://api.coingecko.com/"},
    "frankfurter":  {"name": "Frankfurter FX API",      "url": "https://api.frankfurter.app/"},
    "acled":        {"name": "ACLED Data",               "url": "https://api.acleddata.com/"},
    "finnhub":      {"name": "Finnhub Financial API",   "url": "https://finnhub.io/"},
    "eia":          {"name": "EIA Energy API",           "url": "https://api.eia.gov/"},
    "nasa_firms":   {"name": "NASA FIRMS",               "url": "https://firms.modaps.eosdis.nasa.gov/"},
    "newsdata":     {"name": "NewsData.io",              "url": "https://newsdata.io/"},
    "cloudflare":   {"name": "Cloudflare Radar API",    "url": "https://api.cloudflare.com/"},
    "who_rss":      {"name": "WHO Disease Outbreak News","url": "https://www.who.int/rss-feeds/"},
    "waqi":         {"name": "WAQI Air Quality Index",  "url": "https://waqi.info/"},
    "ripe_bgp":     {"name": "RIPE NCC BGP Data",       "url": "https://stat.ripe.net/"},
    "meteoalarm":   {"name": "Meteoalarm / NOAA",       "url": "https://www.meteoalarm.org/"},
    "gdelt_cyber":  {"name": "GDELT Document API v2",    "url": "https://api.gdeltproject.org/"},
    "gdelt_sanctions": {"name": "GDELT Document API v2", "url": "https://api.gdeltproject.org/"},
    "gdelt_news_geo":  {"name": "GDELT Document API v2", "url": "https://api.gdeltproject.org/"},
}

# Mark key-required providers immediately
if not _KEYS["acled"]:       _CB["acled"].set_key_required()
if not _KEYS["finnhub"]:     _CB["finnhub"].set_key_required()
if not _KEYS["eia"]:         _CB["eia"].set_key_required()
if not _KEYS["nasa_firms"]:  _CB["nasa_firms"].set_key_required()
if not _KEYS["cloudflare"]:  _CB["cloudflare"].set_key_required()
# newsdata is optional: no key = graceful GDELT fallback, so don't set key_required

# Log which keyed providers are active
_active = [k for k in ["acled","finnhub","eia","nasa_firms","newsdata","cloudflare"] if _KEYS.get(k)]
if _active:
    print(f"[Globe API] Keyed providers active: {', '.join(_active)}")
else:
    print("[Globe API] No optional API keys set — using free-tier providers only")


# ──────────────────────────────────────────────────────────────
# Cache
# ──────────────────────────────────────────────────────────────
_cache: dict[str, dict] = {}


async def _fetch_json(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    timeout: float = 15.0,
) -> dict | list:
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.get(url, params=params or {}, headers=headers or {})
        resp.raise_for_status()
        return resp.json()


async def fetch_cached(
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    ttl: int = 300,
) -> dict | list:
    key = url + str(sorted((params or {}).items()))
    now = time.monotonic()
    if key in _cache and now - _cache[key]["ts"] < ttl:
        return _cache[key]["data"]
    try:
        data = await _fetch_json(url, params, headers)
        _cache[key] = {"data": data, "ts": now}
        return data
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 429:
            # Rate-limited — serve stale cache if available, else re-raise
            if key in _cache:
                print(f"[Globe API] 429 from {url[:60]} — serving stale cache")
                return _cache[key]["data"]
        raise
    except Exception:
        # Network error — serve stale cache if available, else re-raise
        if key in _cache:
            return _cache[key]["data"]
        raise


async def guarded_fetch(
    cb_name: str,
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    ttl: int = 300,
) -> dict | list | None:
    """Fetch with circuit-breaker guard. Returns None if circuit open."""
    if cb_name not in _CB:
        _CB[cb_name] = CircuitBreaker(cb_name)
    cb = _CB[cb_name]
    if cb.is_open():
        return None
    try:
        data = await fetch_cached(url, params, headers, ttl)
        cb.success()
        return data
    except httpx.HTTPStatusError as exc:
        # 429 rate-limit: record as soft degraded but don't open circuit immediately
        if exc.response.status_code == 429:
            cb.last_error = "429 Too Many Requests"
            cb.status = "degraded"
            return None
        cb.failure(str(exc))
        return None
    except Exception as exc:
        cb.failure(str(exc))
        return None


# ──────────────────────────────────────────────────────────────
# Provenance stamping
# ──────────────────────────────────────────────────────────────
def _provenance(provider: str, cached: bool = True) -> dict:
    """Build a _provenance block for an event or batch."""
    now_ms = int(time.time() * 1000)
    meta   = _PROVIDER_META.get(provider, {"name": provider, "url": ""})
    cache_info = _cache.get(meta.get("url", provider), {})
    cache_age  = int(time.monotonic() - cache_info["ts"]) if cache_info else 0
    return {
        "provider":        provider,
        "source":          meta["name"],
        "sourceUrl":       meta["url"],
        "retrievedAt":     now_ms,
        "cacheAge":        cache_age,
        "retrievalMethod": "http_cached" if cached else "http_live",
    }


def _stamp(events: list[dict], provider: str) -> list[dict]:
    """Attach _provenance to a list of event dicts in-place."""
    prov = _provenance(provider)
    for e in events:
        e["_provenance"] = prov
    return events


# ──────────────────────────────────────────────────────────────
# WebSocket broadcaster
# ──────────────────────────────────────────────────────────────
class GlobeSocketBroadcaster:
    """Manages connected /ws/globe clients and background fetch-push loop."""

    def __init__(self) -> None:
        self._clients: list = []          # WebSocket objects
        self._task: asyncio.Task | None = None
        self._last_event_ids: dict[str, set[str]] = {}  # layer → set of IDs

    def add_client(self, ws: Any) -> None:
        self._clients.append(ws)
        print(f"[Globe WS] Client connected. Total: {len(self._clients)}")

    def remove_client(self, ws: Any) -> None:
        self._clients = [c for c in self._clients if c is not ws]
        print(f"[Globe WS] Client disconnected. Total: {len(self._clients)}")

    async def _broadcast(self, payload: dict) -> None:
        if not self._clients:
            return
        import json as _json
        msg = _json.dumps(payload)
        dead: list = []
        for ws in list(self._clients):
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.remove_client(ws)

    def _delta(self, layer: str, events: list[dict]) -> list[dict]:
        """Return only events whose ID hasn't been seen for this layer."""
        seen = self._last_event_ids.setdefault(layer, set())
        new_events = [e for e in events if e.get("id") not in seen]
        # Update seen set; cap at 1 000 IDs
        for e in events:
            seen.add(e.get("id", ""))
        if len(seen) > 1000:
            self._last_event_ids[layer] = set(list(seen)[-500:])
        return new_events

    async def _push_cycle(self) -> None:
        """One full fetch-and-push cycle for all layers."""
        now = int(time.time() * 1000)

        # ── Earthquakes ────────────────────────────────────────
        try:
            eq_data = await guarded_fetch(
                "usgs",
                "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
                ttl=120,
            )
            if eq_data:
                events = []
                for f in eq_data.get("features", []):
                    p = f.get("properties", {})
                    g = f.get("geometry", {}).get("coordinates", [0, 0, 0])
                    mag = p.get("mag", 0) or 0
                    events.append({
                        "id":       f.get("id", ""),
                        "title":    f"M{mag:.1f} — {p.get('place', 'Unknown')}",
                        "lat":      g[1], "lng": g[0],
                        "severity": "critical" if mag >= 7 else "high" if mag >= 6 else "medium" if mag >= 5 else "low",
                        "category": "earthquake",
                    })
                _stamp(events, "usgs")
                delta = self._delta("earthquake", events)
                if delta:
                    await self._broadcast({"type": "GLOBE_DELTA", "layer": "earthquake", "events": delta, "timestamp": now})
        except Exception as exc:
            print(f"[Globe WS] EQ push error: {exc}")

        # ── Intelligence push removed (Jarvis refactor) ─────────────────
        pass

        # ── Provider health ────────────────────────────────────
        try:
            providers = [cb.to_dict() for cb in _CB.values()]
            summary = {
                "ok":           sum(1 for p in providers if p["status"] == "ok"),
                "degraded":     sum(1 for p in providers if p["status"] == "degraded"),
                "down":         sum(1 for p in providers if p["status"] == "down"),
                "key_required": sum(1 for p in providers if p["status"] == "key_required"),
                "total":        len(providers),
            }
            await self._broadcast({"type": "GLOBE_HEALTH", "providers": providers,
                                   "summary": summary, "timestamp": now})
        except Exception as exc:
            print(f"[Globe WS] Health push error: {exc}")

    async def run_loop(self, interval_s: float = 30.0) -> None:
        """Background loop disabled to save resources and throttle API spam."""
        print("🌍 [Globe WS] Background OSINT polling heavily throttled for Jarvis mode.")
        while True:
            # We skip the heavy push_cycle to stop background spam.
            await asyncio.sleep(interval_s)

    def start(self) -> None:
        """Launch the background loop as an asyncio task."""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.run_loop(), name="globe_ws_broadcaster")


# ── Singleton broadcaster (imported by main.py) ───────────────
globe_broadcaster = GlobeSocketBroadcaster()


# ──────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────
def _options_response() -> Response:
    return Response(
        status_code=204,
        headers={
            "Access-Control-Allow-Origin":  "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
    )


def _severity_rank(s: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1}.get(s, 0)


async def _parse_layers(request: Request) -> list[str]:
    """Extract optional 'layers' list from JSON body."""
    try:
        body = await request.json()
        return body.get("layers", [])
    except Exception:
        return []


def _layer_on(layers: list[str], layer: str) -> bool:
    """True if layers list is empty (= all on) or layer is explicitly present."""
    return not layers or layer in layers


# ──────────────────────────────────────────────────────────────
# EARTHQUAKES — USGS GeoJSON Feed
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/seismology/v1/listEarthquakes", methods=["POST", "OPTIONS"])
async def list_earthquakes(request: Request):
    if request.method == "OPTIONS":
        return _options_response()

    layers = await _parse_layers(request)
    if not _layer_on(layers, "earthquake"):
        return JSONResponse({"earthquakes": [], "degraded": False, "layerDisabled": True})

    data = await guarded_fetch(
        "usgs",
        "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
        ttl=120,
    )
    if data is None:
        return JSONResponse({
            "earthquakes": [],
            "degraded": True,
            "providerStatus": _CB["usgs"].to_dict(),
        })

    earthquakes = []
    for f in data.get("features", []):
        props = f.get("properties", {})
        geom  = f.get("geometry", {}).get("coordinates", [0, 0, 0])
        mag   = props.get("mag", 0) or 0
        earthquakes.append({
            "id":         f.get("id", ""),
            "place":      props.get("place", "Unknown location"),
            "magnitude":  mag,
            "depthKm":    geom[2] if len(geom) > 2 else 0,
            "location":   {"longitude": geom[0], "latitude": geom[1]},
            "occurredAt": props.get("time", 0),
            "sourceUrl":  props.get("url", ""),
            "severity": (
                "critical" if mag >= 7 else
                "high"     if mag >= 6 else
                "medium"   if mag >= 5 else "low"
            ),
        })
    return JSONResponse({"earthquakes": earthquakes, "degraded": False})


# ──────────────────────────────────────────────────────────────
# MILITARY FLIGHTS — OpenSky Network
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/military/v1/listMilitaryFlights", methods=["POST", "OPTIONS"])
async def list_military_flights(request: Request):
    if request.method == "OPTIONS":
        return _options_response()

    layers = await _parse_layers(request)
    if not _layer_on(layers, "flights"):
        return JSONResponse({"flights": [], "degraded": False, "layerDisabled": True})

    # Use OAuth if available for higher rate limits
    headers = {}
    if _KEYS["opensky_id"] and _KEYS["opensky_sec"]:
        import base64
        creds = base64.b64encode(
            f"{_KEYS['opensky_id']}:{_KEYS['opensky_sec']}".encode()
        ).decode()
        headers = {"Authorization": f"Basic {creds}"}

    data = await guarded_fetch(
        "opensky",
        "https://opensky-network.org/api/states/all",
        params={"lamin": "30", "lomin": "-130", "lamax": "72", "lomax": "50"},
        headers=headers,
        ttl=60,
    )
    if data is None:
        return JSONResponse({
            "flights": [],
            "degraded": True,
            "providerStatus": _CB["opensky"].to_dict(),
        })

    flights = []
    for i, s in enumerate(data.get("states", [])):
        if len(flights) >= 80:
            break
        if not s[5] or not s[6]:
            continue
        if i % 5 == 0:
            flights.append({
                "hexCode":       s[0] or "000000",
                "registration":  (s[1] or "UNKNOWN").strip(),
                "type":          "Military Aircraft",
                "country":       s[2] or "Unknown",
                "location":      {"longitude": s[5], "latitude": s[6]},
                "altitudeFeet":  round((s[7] or 0) * 3.281),
                "velocityKnots": round((s[9] or 0) * 1.944),
                "squawk":        s[14] or "",
                "severity":      "high",
            })
    return JSONResponse({"flights": flights, "degraded": False})


# ──────────────────────────────────────────────────────────────
# CONFLICT — GDELT artgeo (free) or ACLED (keyed, enriched)
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/conflict/v1/listConflictEvents", methods=["POST", "OPTIONS"])
async def list_conflict_events(request: Request):
    if request.method == "OPTIONS":
        return _options_response()

    layers = await _parse_layers(request)
    if not _layer_on(layers, "conflict"):
        return JSONResponse({"events": [], "degraded": False, "layerDisabled": True})

    # ── ACLED (keyed) ─────────────────────────────────────────
    if _KEYS["acled"] and not _CB["acled"].is_open():
        try:
            data = await guarded_fetch(
                "acled",
                "https://api.acleddata.com/acled/read",
                params={
                    "key":         _KEYS["acled"],
                    "email":       os.getenv("ACLED_EMAIL", ""),
                    "event_date":  "2025-01-01",
                    "event_date_where": ">=",
                    "fields":      "event_id_cnty|event_date|event_type|sub_event_type|country|location|latitude|longitude|fatalities|notes",
                    "limit":       50,
                    "format":      "json",
                },
                ttl=300,
            )
            if data and isinstance(data, dict):
                rows = data.get("data", [])
                events = []
                for r in rows:
                    try:
                        lat = float(r.get("latitude", 0))
                        lon = float(r.get("longitude", 0))
                    except (ValueError, TypeError):
                        continue
                    fat = int(r.get("fatalities", 0) or 0)
                    events.append({
                        "id":          r.get("event_id_cnty", ""),
                        "title":       f"{r.get('event_type','')} — {r.get('location','')}",
                        "location":    r.get("location", "Unknown"),
                        "lat":         lat,
                        "lng":         lon,
                        "severity":    "critical" if fat >= 10 else "high" if fat >= 1 else "medium",
                        "category":    "conflict",
                        "description": (r.get("notes", "") or "")[:200],
                        "source":      "ACLED",
                    })
                return JSONResponse({"events": events, "degraded": False, "source": "acled"})
        except Exception:
            pass  # fall through to GDELT

    # ── GDELT fallback ────────────────────────────────────────
    data = await guarded_fetch(
        "gdelt_conflict",
        "https://api.gdeltproject.org/api/v2/doc/doc",
        params={
            "query":      "conflict war explosion attack protest",
            "mode":       "artgeo",
            "format":     "json",
            "maxrecords": "60",
            "timespan":   "24h",
            "sort":       "ToneDesc",
        },
        ttl=300,
    )
    if data is None:
        return JSONResponse({
            "events": [],
            "degraded": True,
            "providerStatus": _CB["gdelt_conflict"].to_dict(),
        })

    events = []
    for a in (data.get("articles", []) or [])[:60]:
        lat = a.get("actiongeo_lat")
        lon = a.get("actiongeo_long")
        if not lat or not lon:
            continue
        try:
            lat, lon = float(lat), float(lon)
        except (ValueError, TypeError):
            continue
        tone = float(a.get("tone", 0) or 0)
        events.append({
            "id":          (a.get("url", "") or "")[:64],
            "title":       (a.get("title", "") or "")[:120],
            "location":    a.get("actiongeo_fullname", "Unknown"),
            "lat":         lat,
            "lng":         lon,
            "severity":    "critical" if tone < -10 else "high" if tone < -5 else "medium",
            "category":    "conflict",
            "description": a.get("domain", "GDELT Intelligence"),
            "source":      "gdelt",
        })
    return JSONResponse({"events": events, "degraded": False, "source": "gdelt"})


# ──────────────────────────────────────────────────────────────
# WILDFIRE — NASA FIRMS (keyed) or EONET (free fallback)
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/wildfire/v1/listFireDetections", methods=["POST", "OPTIONS"])
async def list_fire_detections(request: Request):
    if request.method == "OPTIONS":
        return _options_response()

    layers = await _parse_layers(request)
    if not _layer_on(layers, "wildfire"):
        return JSONResponse({"fireDetections": [], "degraded": False, "layerDisabled": True})

    # ── NASA FIRMS (keyed, high-res) ──────────────────────────
    if _KEYS["nasa_firms"] and not _CB["nasa_firms"].is_open():
        try:
            data = await guarded_fetch(
                "nasa_firms",
                f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{_KEYS['nasa_firms']}/VIIRS_SNPP_NRT/world/1",
                ttl=600,
            )
            # FIRMS returns CSV text
            if data and isinstance(data, str):
                lines = data.strip().split("\n")
                if len(lines) > 1:
                    header = lines[0].split(",")
                    lat_i  = header.index("latitude")  if "latitude"  in header else 0
                    lon_i  = header.index("longitude") if "longitude" in header else 1
                    frp_i  = header.index("frp")       if "frp"       in header else -1
                    detections = []
                    for line in lines[1:201]:
                        cols = line.split(",")
                        try:
                            lat = float(cols[lat_i])
                            lon = float(cols[lon_i])
                            frp = float(cols[frp_i]) if frp_i >= 0 else 0
                        except (ValueError, IndexError):
                            continue
                        detections.append({
                            "id":         f"firms-{lat:.2f}-{lon:.2f}",
                            "title":      "VIIRS Fire Detection",
                            "lat":        lat,
                            "lon":        lon,
                            "brightness": 400,
                            "frp":        frp,
                            "source":     "NASA FIRMS",
                        })
                    return JSONResponse({"fireDetections": detections, "degraded": False, "source": "nasa_firms"})
        except Exception:
            pass

    # ── EONET fallback ────────────────────────────────────────
    data = await guarded_fetch(
        "eonet",
        "https://eonet.gsfc.nasa.gov/api/v3/events",
        params={"status": "open", "category": "wildfires", "days": 7, "limit": 100},
        ttl=300,
    )
    if data is None:
        return JSONResponse({
            "fireDetections": [],
            "degraded": True,
            "providerStatus": _CB["eonet"].to_dict(),
        })

    detections = []
    for ev in data.get("events", []):
        for g in ev.get("geometry", []):
            coords = g.get("coordinates", [])
            if isinstance(coords, list) and len(coords) == 2 and isinstance(coords[0], (int, float)):
                detections.append({
                    "id":         ev.get("id", ""),
                    "title":      ev.get("title", "Wildfire"),
                    "lat":        coords[1],
                    "lon":        coords[0],
                    "brightness": 400,
                    "frp":        0,
                    "source":     "NASA EONET",
                })
                break
    return JSONResponse({"fireDetections": detections, "degraded": False, "source": "eonet"})


# ──────────────────────────────────────────────────────────────
# CLIMATE — NASA EONET (storms, floods, volcanoes, ice)
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/climate/v1/listClimateAnomalies", methods=["POST", "OPTIONS"])
async def list_climate_anomalies(request: Request):
    if request.method == "OPTIONS":
        return _options_response()

    layers = await _parse_layers(request)
    if not _layer_on(layers, "climate"):
        return JSONResponse({"anomalies": [], "degraded": False, "layerDisabled": True})

    data = await guarded_fetch(
        "eonet",
        "https://eonet.gsfc.nasa.gov/api/v3/events",
        params={"status": "open", "days": 3, "limit": 80},
        ttl=300,
    )
    if data is None:
        return JSONResponse({
            "anomalies": [],
            "degraded": True,
            "providerStatus": _CB["eonet"].to_dict(),
        })

    CAT_SEV = {
        "Wildfires": "high", "Severe Storms": "high", "Volcanoes": "critical",
        "Sea and Lake Ice": "medium", "Floods": "high", "Landslides": "medium",
        "Drought": "medium", "Snow": "low", "Dust and Haze": "low",
    }
    anomalies = []
    for ev in data.get("events", []):
        cats = [c.get("title", "") for c in ev.get("categories", [])]
        cat  = cats[0] if cats else "Natural"
        geoms = ev.get("geometry", [])
        if not geoms:
            continue
        g      = geoms[0]
        coords = g.get("coordinates", [])
        if not coords or isinstance(coords[0], list):
            continue
        anomalies.append({
            "id":            ev.get("id", ""),
            "title":         ev.get("title", cat),
            "lat":           coords[1],
            "lng":           coords[0],
            "severity":      CAT_SEV.get(cat, "medium"),
            "category":      cat.lower().replace(" ", "_"),
            "categoryLabel": cat,
        })
    return JSONResponse({"anomalies": anomalies, "degraded": False})


# ──────────────────────────────────────────────────────────────
# MARKET TICKERS — CoinGecko + Frankfurter + FINNHUB (keyed)
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/market/v1/getTicker", methods=["POST", "OPTIONS"])
async def get_ticker(request: Request):
    if request.method == "OPTIONS":
        return _options_response()

    tickers: list[dict] = []

    # ── CoinGecko (free) ──────────────────────────────────────
    cg = await guarded_fetch(
        "coingecko",
        "https://api.coingecko.com/api/v3/simple/price",
        params={
            "ids":           "bitcoin,ethereum,solana",
            "vs_currencies": "usd",
            "include_24hr_change": "true",
        },
        ttl=60,
    )
    if cg:
        for coin_id, vals in cg.items():
            ticker_map = {"bitcoin": "BTC", "ethereum": "ETH", "solana": "SOL"}
            sym = ticker_map.get(coin_id, coin_id.upper()[:4])
            price  = vals.get("usd", 0)
            change = vals.get("usd_24h_change", 0) or 0
            tickers.append({
                "symbol":       sym,
                "value":        round(price, 2),
                "delta":        round(change * price / 100, 2),
                "deltaPercent": round(change, 2),
                "source":       "coingecko",
            })

    # ── Frankfurter forex (free) ──────────────────────────────
    fx = await guarded_fetch(
        "frankfurter",
        "https://api.frankfurter.app/latest",
        params={"from": "USD", "to": "EUR,GBP,JPY,CNY"},
        ttl=300,
    )
    if fx:
        base_map = {"EUR": "EUR", "GBP": "GBP", "JPY": "JPY/100", "CNY": "CNY"}
        for sym, rate in (fx.get("rates") or {}).items():
            label = base_map.get(sym, sym)
            tickers.append({
                "symbol":       label,
                "value":        round(float(rate), 4),
                "delta":        0,
                "deltaPercent": 0,
                "source":       "frankfurter",
            })

    # ── FINNHUB stocks (keyed) ────────────────────────────────
    if _KEYS["finnhub"] and not _CB["finnhub"].is_open():
        for sym in ["SPY", "QQQ", "GLD", "OIL"]:
            try:
                d = await guarded_fetch(
                    "finnhub",
                    "https://finnhub.io/api/v1/quote",
                    params={"symbol": sym, "token": _KEYS["finnhub"]},
                    ttl=60,
                )
                if d and d.get("c"):
                    price  = float(d["c"])
                    prev   = float(d.get("pc", price))
                    change = price - prev
                    tickers.append({
                        "symbol":       sym,
                        "value":        round(price, 2),
                        "delta":        round(change, 2),
                        "deltaPercent": round(change / prev * 100, 2) if prev else 0,
                        "source":       "finnhub",
                    })
            except Exception:
                pass

    # ── EIA energy (keyed) ────────────────────────────────────
    if _KEYS["eia"] and not _CB["eia"].is_open():
        try:
            d = await guarded_fetch(
                "eia",
                "https://api.eia.gov/v2/petroleum/pri/spt/data/",
                params={
                    "api_key":       _KEYS["eia"],
                    "frequency":     "daily",
                    "data[0]":       "value",
                    "sort[0][column]": "period",
                    "sort[0][direction]": "desc",
                    "length":        2,
                },
                ttl=3600,
            )
            if d:
                rows = (d.get("response", {}) or {}).get("data", [])
                if len(rows) >= 2:
                    latest = float(rows[0].get("value", 0))
                    prev   = float(rows[1].get("value", latest))
                    tickers.append({
                        "symbol":       "WTI OIL",
                        "value":        round(latest, 2),
                        "delta":        round(latest - prev, 2),
                        "deltaPercent": round((latest - prev) / prev * 100, 2) if prev else 0,
                        "source":       "eia",
                    })
        except Exception:
            pass

    return JSONResponse({"tickers": tickers, "degraded": not tickers})


# ──────────────────────────────────────────────────────────────
# GDELT INTELLIGENCE  (/api/intelligence/v1/searchGdeltDocuments)
# ──────────────────────────────────────────────────────────────
_TOPIC_QUERIES: dict[str, str] = {
    "military":   "military conflict war airstrike troops",
    "cyber":      "cyberattack hacking breach ransomware",
    "sanctions":  "sanctions economic war tariff",
    "energy":     "oil gas pipeline energy shortage",
    "climate":    "climate drought flood wildfire",
    "nuclear":    "nuclear weapon missile ballistic",
    "migration":  "refugee migration border displacement",
    "finance":    "financial crisis market crash bank",
    "health":     "pandemic outbreak disease WHO",
    "space":      "space satellite launch orbit",
}

@router.api_route("/api/intelligence/v1/searchGdeltDocuments", methods=["POST", "OPTIONS"])
async def search_gdelt_documents(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        body = await request.json()
    except Exception:
        body = {}
    topic      = body.get("topic", "military")
    max_records = min(int(body.get("maxRecords", 25)), 50)
    query      = _TOPIC_QUERIES.get(topic, topic)

    # Use dedicated CB keys for high-frequency polling topics so they
    # can't trip and block the user-facing Intel panel (gdelt_intel).
    _TOPIC_CB_MAP = {"cyber": "gdelt_cyber", "sanctions": "gdelt_sanctions"}
    cb_name = _TOPIC_CB_MAP.get(topic, "gdelt_intel")

    data = await guarded_fetch(
        cb_name,
        "https://api.gdeltproject.org/api/v2/doc/doc",
        params={
            "query":      f"{query} sourcelang:eng",
            "mode":       "artlist",
            "format":     "json",
            "maxrecords": str(max_records),
            "timespan":   "24h",
            "sort":       "DateDesc",
        },
        ttl=300,
    )
    if data is None:
        return JSONResponse({
            "articles": [],
            "degraded": True,
            "providerStatus": _CB[cb_name].to_dict(),
        })

    articles = []
    for a in (data.get("articles", []) or [])[:max_records]:
        articles.append({
            "title":    (a.get("title")    or "")[:160],
            "url":      a.get("url")       or "",
            "source":   a.get("domain")    or "",
            "date":     a.get("seendate")  or "",
            "image":    a.get("socialimage") or "",
            "language": a.get("language")  or "English",
            "tone":     round(float(a.get("tone", 0) or 0), 2),
        })
    return JSONResponse({"articles": articles, "degraded": False})


# ──────────────────────────────────────────────────────────────
# LIVE NEWS  (/api/news/v1/listNewsArticles)
# ──────────────────────────────────────────────────────────────
_MODE_QUERIES: dict[str, str] = {
    "world":   "geopolitics conflict security crisis",
    "tech":    "technology AI cyber semiconductor quantum",
    "finance": "markets economy finance trade Fed inflation",
    "happy":   "breakthrough innovation progress science",
}

# NewsData.io category map (used when key is present)
_NEWSDATA_CATEGORIES: dict[str, str] = {
    "world":   "world,politics",
    "tech":    "technology,science",
    "finance": "business",
    "happy":   "science,health",
}

@router.api_route("/api/news/v1/listNewsArticles", methods=["POST", "OPTIONS"])
async def list_news_articles(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        body = await request.json()
    except Exception:
        body = {}
    mode  = body.get("mode", "world")
    query = _MODE_QUERIES.get(mode, "world news")

    # ── Primary: NewsData.io (when key is available) ──────────────────────
    if _KEYS["newsdata"] and not _CB["newsdata"].is_open():
        data = await guarded_fetch(
            "newsdata",
            "https://newsdata.io/api/1/latest",
            params={
                "apikey":         _KEYS["newsdata"],
                "q":              query,
                "language":       "en",
                "category":       _NEWSDATA_CATEGORIES.get(mode, "world"),
                "size":           "15",
                "prioritydomain": "top",
            },
            ttl=300,
        )
        if data is not None and data.get("status") == "success":
            articles = []
            for a in (data.get("results") or [])[:15]:
                articles.append({
                    "title":       (a.get("title")       or "")[:160],
                    "url":         a.get("link")          or "",
                    "source":      a.get("source_name")   or a.get("source_id") or "",
                    "date":        a.get("pubDate")       or "",
                    "image":       a.get("image_url")     or "",
                    "language":    a.get("language")      or "en",
                    "tone":        0.0,  # NewsData.io doesn't provide tone scores
                    "description": (a.get("description") or "")[:300],
                    "category":    (a.get("category")    or [None])[0],
                    "country":     (a.get("country")     or [None])[0],
                    "provider":    "newsdata",
                })
            return JSONResponse({"articles": articles, "degraded": False, "source": "newsdata.io"})

    # ── Fallback: GDELT (free, no key) ────────────────────────────────────
    data = await guarded_fetch(
        "gdelt_news",
        "https://api.gdeltproject.org/api/v2/doc/doc",
        params={
            "query":      f"{query} sourcelang:eng",
            "mode":       "artlist",
            "format":     "json",
            "maxrecords": "15",
            "timespan":   "3h",
            "sort":       "DateDesc",
        },
        ttl=300,
    )
    if data is None:
        return JSONResponse({
            "articles": [],
            "degraded": True,
            "providerStatus": _CB["gdelt_news"].to_dict(),
        })

    articles = []
    for a in (data.get("articles", []) or [])[:15]:
        articles.append({
            "title":    (a.get("title")    or "")[:160],
            "url":      a.get("url")       or "",
            "source":   a.get("domain")    or "",
            "date":     a.get("seendate")  or "",
            "image":    a.get("socialimage") or "",
            "language": a.get("language")  or "English",
            "tone":     round(float(a.get("tone", 0) or 0), 2),
            "provider": "gdelt",
        })
    return JSONResponse({"articles": articles, "degraded": False, "source": "gdelt"})


# ──────────────────────────────────────────────────────────────
# NEWS GEO  (/api/news/v1/listNewsGeo)
# Returns geo-tagged news events for globe map overlay.
# Uses GDELT artgeo mode — only articles with resolved coordinates.
# ──────────────────────────────────────────────────────────────
_NEWS_GEO_QUERIES: dict[str, str] = {
    "world":   "crisis conflict protest government election war",
    "tech":    "AI technology cyber hack satellite launch",
    "finance": "economy market crash trade sanctions bank",
    "happy":   "breakthrough discovery innovation science climate",
}

@router.api_route("/api/news/v1/listNewsGeo", methods=["POST", "OPTIONS"])
async def list_news_geo(request: Request):
    """Geo-tagged world news for the globe map layer (artgeo mode)."""
    if request.method == "OPTIONS":
        return _options_response()
    try:
        body = await request.json()
    except Exception:
        body = {}
    mode  = body.get("mode", "world")
    query = _NEWS_GEO_QUERIES.get(mode, "world news crisis")

    data = await guarded_fetch(
        "gdelt_news_geo",
        "https://api.gdeltproject.org/api/v2/doc/doc",
        params={
            "query":      f"{query} sourcelang:eng",
            "mode":       "artgeo",
            "format":     "json",
            "maxrecords": "60",
            "timespan":   "6h",
            "sort":       "ToneDesc",
        },
        ttl=300,
    )
    if data is None:
        return JSONResponse({
            "events": [],
            "degraded": True,
            "providerStatus": _CB["gdelt_news_geo"].to_dict(),
        })

    events = []
    for a in (data.get("articles", []) or [])[:60]:
        lat = a.get("actiongeo_lat")
        lon = a.get("actiongeo_long")
        if not lat or not lon:
            continue
        try:
            lat, lon = float(lat), float(lon)
        except (ValueError, TypeError):
            continue
        tone = float(a.get("tone", 0) or 0)
        events.append({
            "id":          (a.get("url") or "")[:64],
            "title":       (a.get("title") or "")[:120],
            "url":         a.get("url") or "",
            "source":      a.get("domain") or "",
            "date":        a.get("seendate") or "",
            "location":    a.get("actiongeo_fullname") or "Unknown",
            "lat":         lat,
            "lng":         lon,
            "tone":        round(tone, 2),
            "severity":    "critical" if tone < -10 else "high" if tone < -5 else "medium" if tone < 0 else "low",
            "category":    "news",
        })
    _stamp(events, "gdelt_news")
    return JSONResponse({"events": events, "degraded": False})


# ──────────────────────────────────────────────────────────────
# COUNTRY INTELLIGENCE
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/intel/v1/getCountryIntelligence", methods=["POST", "OPTIONS"])
async def get_country_intelligence(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        body = await request.json()
    except Exception:
        body = {}
    country = body.get("country", "Ukraine")

    data = await guarded_fetch(
        "gdelt_intel",
        "https://api.gdeltproject.org/api/v2/doc/doc",
        params={
            "query":      f"{country} sourcelang:eng",
            "mode":       "artlist",
            "format":     "json",
            "maxrecords": "10",
            "timespan":   "12h",
            "sort":       "DateDesc",
        },
        ttl=300,
    )
    if data is None:
        return JSONResponse({
            "country": country, "articles": [],
            "degraded": True,
            "providerStatus": _CB["gdelt_intel"].to_dict(),
        })

    articles_raw = (data.get("articles") or [])
    articles = [
        {
            "title":  a.get("title", ""),
            "url":    a.get("url", ""),
            "source": a.get("domain", ""),
            "date":   a.get("seendate", ""),
            "tone":   round(float(a.get("tone", 0) or 0), 2),
        }
        for a in articles_raw
    ]
    avg = round(sum(a["tone"] for a in articles) / len(articles), 2) if articles else 0.0
    return JSONResponse({
        "country":      country,
        "articles":     articles,
        "averageTone":  avg,
        "articleCount": len(articles),
        "degraded":     False,
    })


# ──────────────────────────────────────────────────────────────
# INTERNET OUTAGE LAYER — Cloudflare Radar (keyed)
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/infrastructure/v1/listInternetOutages", methods=["POST", "OPTIONS"])
async def list_internet_outages(request: Request):
    if request.method == "OPTIONS":
        return _options_response()

    layers = await _parse_layers(request)
    if not _layer_on(layers, "infrastructure"):
        return JSONResponse({"outages": [], "degraded": False, "layerDisabled": True})

    if _CB["cloudflare"].is_open():
        return JSONResponse({
            "outages": [],
            "degraded": _CB["cloudflare"].status == "down",
            "keyRequired": _CB["cloudflare"].status == "key_required",
            "hint": "Set CLOUDFLARE_API_TOKEN to enable this layer",
        })

    data = await guarded_fetch(
        "cloudflare",
        "https://api.cloudflare.com/client/v4/radar/annotations/outages",
        headers={"Authorization": f"Bearer {_KEYS['cloudflare']}"},
        ttl=300,
    )
    if data is None:
        return JSONResponse({
            "outages": [],
            "degraded": True,
            "providerStatus": _CB["cloudflare"].to_dict(),
        })

    outages = []
    result = data.get("result", {}) or {}
    for item in (result.get("annotations") or []):
        outages.append({
            "id":          item.get("id", ""),
            "description": item.get("description", ""),
            "startTime":   item.get("startTime", ""),
            "endTime":     item.get("endTime", ""),
            "asns":        item.get("asns", []),
            "locations":   item.get("locations", []),
        })
    return JSONResponse({"outages": outages, "degraded": False})


# ──────────────────────────────────────────────────────────────
# RSS PROXY (backward compat)
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/rss-proxy", methods=["GET", "OPTIONS"])
async def rss_proxy(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    url = request.query_params.get("url", "")
    if not url:
        return JSONResponse({"error": "Missing url param"}, status_code=400)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.get(url, headers={"User-Agent": "SPARK-Globe/3.0"})
        return Response(content=r.content, media_type="application/xml")
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=502)


# ──────────────────────────────────────────────────────────────
# PROVIDER HEALTH DASHBOARD
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/globe/v1/getProviderHealth", methods=["GET", "POST", "OPTIONS"])
async def get_provider_health(request: Request):
    if request.method == "OPTIONS":
        return _options_response()

    providers = [cb.to_dict() for cb in _CB.values()]
    ok_count       = sum(1 for p in providers if p["status"] == "ok")
    degraded_count = sum(1 for p in providers if p["status"] == "degraded")
    down_count     = sum(1 for p in providers if p["status"] == "down")
    key_req_count  = sum(1 for p in providers if p["status"] == "key_required")

    # surface which keys are present (name only, NOT values)
    optional_keys = {k: (v is not None) for k, v in _KEYS.items()}

    return JSONResponse({
        "providers":     providers,
        "summary": {
            "ok":           ok_count,
            "degraded":     degraded_count,
            "down":         down_count,
            "key_required": key_req_count,
            "total":        len(providers),
        },
        "optionalKeys":  optional_keys,
        "generatedAt":   int(time.time() * 1000),
    })


# ──────────────────────────────────────────────────────────────
# SIGNAL FUSION ENGINE
# ──────────────────────────────────────────────────────────────
def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def _gather_fusion_data() -> dict[str, list]:
    async def _eq():
        d = await guarded_fetch("usgs",
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson",
            ttl=300)
        if not d:
            return []
        out = []
        for f in d.get("features", []):
            p = f.get("properties", {})
            g = f.get("geometry", {}).get("coordinates", [0, 0, 0])
            mag = p.get("mag", 0) or 0
            out.append({
                "id": f.get("id", ""), "type": "earthquake",
                "title": p.get("place", "Unknown"),
                "severity": "critical" if mag >= 7 else "high" if mag >= 6 else "medium" if mag >= 5 else "low",
                "lat": g[1], "lon": g[0], "ts": p.get("time", 0),
                "meta": {"magnitude": mag},
            })
        return out

    async def _eonet():
        d = await guarded_fetch("eonet",
            "https://eonet.gsfc.nasa.gov/api/v3/events",
            params={"status": "open", "days": 3, "limit": 60}, ttl=300)
        if not d:
            return []
        CAT_SEV = {"Wildfires": "high", "Severe Storms": "high", "Volcanoes": "critical",
                   "Sea and Lake Ice": "medium", "Floods": "high", "Landslides": "medium"}
        out = []
        for ev in d.get("events", []):
            cats = [c.get("title", "") for c in ev.get("categories", [])]
            cat = cats[0] if cats else "Natural"
            for g in ev.get("geometry", []):
                c = g.get("coordinates", [])
                if isinstance(c, list) and len(c) == 2 and isinstance(c[0], (int, float)):
                    out.append({
                        "id": ev.get("id", ""), "type": cat.lower().replace(" ", "_"),
                        "title": ev.get("title", cat),
                        "severity": CAT_SEV.get(cat, "medium"),
                        "lat": c[1], "lon": c[0], "ts": 0, "meta": {"category": cat},
                    })
                    break
        return out

    async def _conflict():
        d = await guarded_fetch("gdelt_conflict",
            "https://api.gdeltproject.org/api/v2/doc/doc",
            params={"query": "conflict war explosion attack",
                    "mode": "artgeo", "format": "json",
                    "maxrecords": "50", "timespan": "24h", "sort": "ToneDesc"},
            ttl=300)
        if not d:
            return []
        out = []
        for a in (d.get("articles", []) or [])[:50]:
            lat = a.get("actiongeo_lat")
            lon = a.get("actiongeo_long")
            if not lat or not lon:
                continue
            try:
                lat, lon = float(lat), float(lon)
            except (ValueError, TypeError):
                continue
            tone = float(a.get("tone", 0) or 0)
            out.append({
                "id": (a.get("url", "") or "")[:64], "type": "conflict",
                "title": (a.get("title", "") or "")[:120],
                "severity": "critical" if tone < -10 else "high" if tone < -5 else "medium",
                "lat": lat, "lon": lon, "ts": 0,
                "meta": {"tone": tone, "domain": a.get("domain", "")},
            })
        return out

    eqs, eonet_evts, conflicts = await asyncio.gather(_eq(), _eonet(), _conflict())
    return {"earthquake": eqs, "natural": eonet_evts, "conflict": conflicts}


def _build_fusion_items(sources: dict[str, list]) -> list[dict[str, Any]]:
    all_events: list[dict] = []
    for evts in sources.values():
        all_events.extend(evts)
    if not all_events:
        return []

    CLUSTER_KM = 600
    n = len(all_events)
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

    def _score(cl: list[int]) -> float:
        ranks = [_severity_rank(all_events[i]["severity"]) for i in cl]
        types = {all_events[i]["type"] for i in cl}
        return max(ranks) * len(cl) * (1.5 if len(types) > 1 else 1.0)

    clusters.sort(key=_score, reverse=True)

    PAIRS = {
        ("earthquake", "wildfire"):    ("ground rupture destabilises terrain", "increased fire ignition risk"),
        ("earthquake", "conflict"):    ("infrastructure collapse", "civil unrest and resource conflict"),
        ("earthquake", "natural"):     ("seismic shaking", "secondary natural hazard triggered"),
        ("wildfire", "conflict"):      ("resource scarcity from fire damage", "population displacement tension"),
        ("severe_storms", "conflict"): ("storm disrupts governance zones", "power vacuum exploitation risk"),
        ("conflict", "earthquake"):    ("conflict limits emergency response", "compounded disaster impact"),
        ("floods", "conflict"):        ("flood displaces populations", "humanitarian access blocked"),
        ("volcanoes", "earthquake"):   ("volcanic stress transfer", "seismic cluster activation"),
    }

    fusion_items: list[dict[str, Any]] = []
    for idx, cl in enumerate(clusters[:6]):
        evts = [all_events[i] for i in cl]
        types = list({e["type"] for e in evts})
        evts_s = sorted(evts, key=lambda e: _severity_rank(e["severity"]), reverse=True)
        cause_evt, effect_evt = evts_s[0], (evts_s[1] if len(evts_s) > 1 else evts_s[0])

        pair_key = (cause_evt["type"], effect_evt["type"])
        cause_d, effect_d = PAIRS.get(
            pair_key,
            PAIRS.get(
                (effect_evt["type"], cause_evt["type"]),
                (f"{cause_evt['type'].replace('_',' ')} event",
                 f"cascading impact on {effect_evt['type'].replace('_',' ')}"),
            ),
        )

        type_div   = min(len(types) / 3.0, 1.0)
        sev_score  = max(_severity_rank(e["severity"]) for e in evts) / 4.0
        size_score = min(len(evts) / 8.0, 1.0)
        confidence = round(min(0.4 * type_div + 0.35 * sev_score + 0.25 * size_score, 0.97), 2)

        clat = sum(e["lat"] for e in evts) / len(evts)
        clon = sum(e["lon"] for e in evts) / len(evts)
        max_rank = max(_severity_rank(e["severity"]) for e in evts)
        severity  = {4: "critical", 3: "high", 2: "medium", 1: "low"}.get(max_rank, "low")

        entities: list[str] = []
        seen_e: set[str] = set()
        for e in evts[:5]:
            for w in e["title"].split():
                if len(w) > 3 and w[0].isupper() and w not in seen_e:
                    seen_e.add(w)
                    entities.append(w)
                if len(entities) >= 5:
                    break

        present = {e["type"] for e in evts}
        all_t = {"earthquake", "conflict", "wildfire"}
        data_gaps = [f"No {t} data in corridor" for t in list(all_t - present)[:2]] or \
                    ["Real-time satellite imagery pending"]

        type_label  = " + ".join(t.replace("_", " ").title() for t in types[:2])
        region_hint = cause_evt["title"][:40].rstrip(",. ")
        title   = f"{type_label} Convergence — {region_hint}"
        summary = (
            f"{len(evts)} correlated signal{'s' if len(evts)>1 else ''} across "
            f"{len(types)} data stream{'s' if len(types)>1 else ''} within a {CLUSTER_KM} km corridor. "
            f"Cross-source confidence: {int(confidence*100)}%. "
            f"Primary vector: {cause_evt['title'][:60]}."
        )

        fusion_items.append({
            "id":          f"fusion-{idx}-{int(time.time())}",
            "severity":    severity,
            "confidence":  confidence,
            "title":       title,
            "summary":     summary,
            "causeEvent":  cause_d,
            "effectEvent": effect_d,
            "entities":    entities,
            "dataGaps":    data_gaps,
            "region":      region_hint,
            "lat":         clat,
            "lon":         clon,
            "eventCount":  len(evts),
            "sourceTypes": types,
            "timestamp":   int(time.time() * 1000),
        })
    return fusion_items


@router.api_route("/api/globe/v1/getFusionSummary", methods=["POST", "GET", "OPTIONS"])
async def get_fusion_summary(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    try:
        sources = await _gather_fusion_data()
        items   = _build_fusion_items(sources)
        return JSONResponse({
            "items":        items,
            "generatedAt":  int(time.time() * 1000),
            "sourceCounts": {k: len(v) for k, v in sources.items()},
        })
    except Exception as e:
        import traceback; traceback.print_exc()
        return JSONResponse({"items": [], "generatedAt": int(time.time() * 1000), "sourceCounts": {}})


# ──────────────────────────────────────────────────────────────
# NEW FREE LAYERS — V4
# ──────────────────────────────────────────────────────────────

# ── Layer 14: Disease Alerts (WHO Disease Outbreak News RSS) ──
@router.api_route("/api/health/v1/listDiseaseAlerts", methods=["POST", "GET", "OPTIONS"])
async def list_disease_alerts(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    URL = "https://www.who.int/rss-feeds/news-english.xml"
    try:
        async with httpx.AsyncClient(timeout=12) as client:
            r = await client.get(URL)
            r.raise_for_status()
        root  = ET.fromstring(r.text)
        items = root.findall(".//item")
        alerts: list[dict] = []
        for it in items[:30]:
            title = (it.findtext("title") or "").strip()
            link  = (it.findtext("link")  or "").strip()
            desc  = (it.findtext("description") or "").strip()[:200]
            # Simple geo heuristic: look for known disease/outbreak keywords
            kw = title.lower()
            if not any(w in kw for w in ["outbreak", "disease", "virus", "fever", "cholera",
                                          "ebola", "mpox", "dengue", "malaria", "polio", "alert",
                                          "emergency", "epidemic", "pandemic"]):
                continue
            alerts.append({
                "id":       link[:64] or title[:40],
                "title":    title,
                "summary":  desc,
                "category": "disease",
                "severity": "high" if any(w in kw for w in ["outbreak", "epidemic", "emergency"]) else "medium",
                "lat":      0.0, "lng": 0.0,  # WHO RSS has no geo; FE uses heatmap
                "url":      link,
            })
        _stamp(alerts, "who_rss")
        return JSONResponse({"alerts": alerts, "total": len(alerts),
                             "degraded": False, "_provenance": _provenance("who_rss")})
    except Exception as exc:
        print(f"[WHO RSS] {exc}")
        _CB["who_rss"].failure(str(exc))
        return JSONResponse({"alerts": [], "total": 0, "degraded": True,
                             "error": str(exc), "_provenance": _provenance("who_rss")})


# ── Layer 15: Air Quality Alerts (OpenAQ free API) ──
@router.api_route("/api/airquality/v1/listAirQualityAlerts", methods=["POST", "GET", "OPTIONS"])
async def list_air_quality_alerts(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    # OpenAQ v3 — completely free, no key required
    URL = "https://api.openaq.org/v3/locations"
    data = await guarded_fetch(
        "waqi", URL,
        params={"limit": 100, "order_by": "lastUpdated", "sort": "desc",
                "parameters_id": "2"},  # pm25 = parameter id 2
        headers={"Accept": "application/json"},
        ttl=300,
    )
    if data is None:
        return JSONResponse({"alerts": [], "degraded": True, "_provenance": _provenance("waqi")})
    alerts: list[dict] = []
    for loc in (data.get("results") or [])[:60]:
        coords = loc.get("coordinates") or {}
        lat = coords.get("latitude")
        lng = coords.get("longitude")
        if lat is None or lng is None:
            continue
        sensors = loc.get("sensors") or []
        aqi_val = None
        for s in sensors:
            last = (s.get("latest") or {}).get("value")
            if last is not None:
                aqi_val = last
                break
        if aqi_val is None:
            continue
        aqi_val = round(float(aqi_val), 1)
        severity = ("critical" if aqi_val > 200 else
                    "high"     if aqi_val > 150 else
                    "medium"   if aqi_val > 100 else
                    "low")
        if severity == "low":
            continue
        alerts.append({
            "id":       str(loc.get("id", "")),
            "title":    f"PM2.5 AQI {aqi_val} — {loc.get('name','Unknown')}",
            "lat":      float(lat), "lng": float(lng),
            "severity": severity,
            "category": "airquality",
            "aqi":      aqi_val,
        })
    _stamp(alerts, "waqi")
    return JSONResponse({"alerts": alerts, "total": len(alerts),
                         "degraded": False, "_provenance": _provenance("waqi")})


# ── Layer 16: BGP / Network Alerts (RIPE NCC Routing Info) ──
@router.api_route("/api/bgp/v1/listNetworkAlerts", methods=["POST", "GET", "OPTIONS"])
async def list_network_alerts(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    URL = "https://stat.ripe.net/data/country-routing-stats/data.json"
    # Fetch top 5 countries routing stats as a proxy for BGP anomalies
    countries = ["US", "RU", "CN", "IR", "KP"]
    alerts: list[dict] = []
    country_coords = {
        "US": (37.09, -95.71), "RU": (61.52, 105.31),
        "CN": (35.86, 104.19), "IR": (32.42, 53.68),
        "KP": (40.33, 127.51),
    }
    cc_data = await guarded_fetch(
        "ripe_bgp",
        "https://stat.ripe.net/data/rir-stats-country/data.json",
        params={"resource": "world"},
        ttl=600,
    )
    # Fall back to per-country routing stats
    try:
        for cc in countries:
            d = await guarded_fetch(
                "ripe_bgp", URL,
                params={"resource": cc, "starttime": "now-1d"},
                ttl=600,
            )
            if not d:
                continue
            result = (d.get("data") or {})
            origs  = result.get("originating_asns", 0) or 0
            pfs    = result.get("prefixes",          0) or 0
            lat, lng = country_coords.get(cc, (0.0, 0.0))
            alerts.append({
                "id":          f"bgp-{cc}",
                "title":       f"BGP Routing — {cc}: {origs} ASNs, {pfs} prefixes",
                "lat":         lat, "lng": lng,
                "severity":    "low",
                "category":    "network",
                "asn_count":   origs,
                "prefix_count": pfs,
                "country":     cc,
            })
    except Exception as exc:
        print(f"[RIPE BGP] {exc}")
    _stamp(alerts, "ripe_bgp")
    return JSONResponse({"alerts": alerts, "total": len(alerts),
                         "degraded": len(alerts) == 0,
                         "_provenance": _provenance("ripe_bgp")})


# ── Layer 17: Displacement Events (UNHCR Operational Data Portal) ──
@router.api_route("/api/displacement/v1/listDisplacementEvents", methods=["POST", "GET", "OPTIONS"])
async def list_displacement_events(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    # UNHCR PopStats — free, no key
    URL = "https://api.unhcr.org/population/v1/population/"
    data = await guarded_fetch(
        "who_rss",   # reuse who_rss CB for humanitarian data
        URL,
        params={"limit": 50, "yearFrom": "2023", "CF_STATUS": "1",
                "page": "1", "sortBy": "refugees+desc"},
        headers={"Accept": "application/json"},
        ttl=3600,
    )
    if data is None:
        return JSONResponse({"events": [], "degraded": True, "_provenance": _provenance("who_rss")})

    # Country code → rough centroid
    _CC_LAT: dict[str, tuple[float, float]] = {
        "SY": (34.8, 38.9), "AF": (33.9, 67.7), "SS": (6.9, 31.3),
        "SO": (5.1, 46.2),  "UA": (48.4, 31.2), "CD": (-4.0, 21.8),
        "MM": (17.1, 96.7), "VE": (8.0, -66.6), "ET": (9.1, 40.5),
        "SD": (12.8, 30.2),
    }
    events: list[dict] = []
    for row in (data.get("items") or [])[:40]:
        cc = (row.get("coo_iso") or "").upper()
        refugees = int(row.get("refugees", 0) or 0)
        if refugees < 1000:
            continue
        lat, lng = _CC_LAT.get(cc, (0.0, 0.0))
        events.append({
            "id":        f"disp-{cc}-{row.get('year', 0)}",
            "title":     f"Displacement — {row.get('coo_name', cc)}: {refugees:,} refugees",
            "lat":       lat, "lng": lng,
            "severity":  "critical" if refugees > 1_000_000 else "high" if refugees > 100_000 else "medium",
            "category":  "displacement",
            "count":     refugees,
            "year":      row.get("year"),
            "origin":    row.get("coo_name", cc),
        })
    _stamp(events, "who_rss")
    return JSONResponse({"events": events, "total": len(events),
                         "degraded": False, "_provenance": _provenance("who_rss")})


# ── Layer 18: Economic Indicators (World Bank Open API — free) ──
@router.api_route("/api/economy/v1/getEconomicIndicators", methods=["POST", "GET", "OPTIONS"])
async def get_economic_indicators(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    # World Bank — GDP growth rate, no key needed
    WB_URL = "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.KD.ZG"
    data = await guarded_fetch(
        "frankfurter",   # reuse FX CB for economic data
        WB_URL,
        params={"format": "json", "mrv": "1", "per_page": "30",
                "source": "2"},
        ttl=3600,
    )
    _CC_COORD: dict[str, tuple[float, float]] = {
        "US": (37.1, -95.7), "CN": (35.8, 104.2), "RU": (61.5, 105.3),
        "DE": (51.2, 10.4),  "JP": (36.2, 138.2), "GB": (55.4, -3.4),
        "FR": (46.2, 2.2),   "IN": (20.6, 78.9),  "BR": (-14.2, -51.9),
        "CA": (56.1, -106.3), "AU": (-25.3, 133.8), "ZA": (-30.6, 22.9),
        "NG": (9.1, 8.7),    "MX": (23.6, -102.5), "AR": (-38.4, -63.6),
        "TK": (38.9, 35.2),  "SA": (23.9, 45.1),  "EG": (26.8, 30.8),
        "ID": (-0.8, 113.9), "PK": (30.4, 69.3),
    }
    indicators: list[dict] = []
    if data and isinstance(data, list) and len(data) > 1:
        for row in (data[1] or [])[:40]:
            val = row.get("value")
            if val is None:
                continue
            cc  = (row.get("countryiso3code") or row.get("country", {}).get("id", "")).upper()
            if cc not in _CC_COORD:
                continue
            val = round(float(val), 2)
            lat, lng = _CC_COORD[cc]
            indicators.append({
                "id":        f"gdp-{cc}-{row.get('date','')}",
                "title":     f"GDP Growth {cc}: {val:+.1f}%",
                "lat":       lat, "lng": lng,
                "severity":  "critical" if val < -5 else "high" if val < 0 else "low",
                "category":  "economy",
                "value":     val,
                "indicator": "GDP Growth (% annual)",
                "country":   (row.get("country") or {}).get("value", cc),
                "year":      row.get("date"),
            })
    _stamp(indicators, "frankfurter")
    return JSONResponse({"indicators": indicators, "total": len(indicators),
                         "degraded": len(indicators) == 0,
                         "_provenance": _provenance("frankfurter")})


# ── Layer 19: Vessel / Maritime Alerts (GDELT maritime query) ──
@router.api_route("/api/shipping/v1/listVesselAlerts", methods=["POST", "GET", "OPTIONS"])
async def list_vessel_alerts(request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    data = await guarded_fetch(
        "gdelt_conflict",
        "https://api.gdeltproject.org/api/v2/doc/doc",
        params={"query": "ship tanker vessel maritime piracy drone attack sea",
                "mode": "artgeo", "format": "json",
                "maxrecords": "25", "timespan": "24h", "sort": "ToneDesc"},
        ttl=300,
    )
    alerts: list[dict] = []
    if data:
        for a in (data.get("articles") or [])[:25]:
            lat = a.get("actiongeo_lat")
            lon = a.get("actiongeo_long")
            if not lat or not lon:
                continue
            try:
                lat, lon = float(lat), float(lon)
            except (ValueError, TypeError):
                continue
            tone  = float(a.get("tone", 0) or 0)
            alerts.append({
                "id":       (a.get("url") or "")[:64],
                "title":    (a.get("title") or "")[:120],
                "lat":      lat, "lng": lon,
                "severity": "critical" if tone < -10 else "high" if tone < -5 else "medium",
                "category": "shipping",
                "url":      a.get("url", ""),
            })
    _stamp(alerts, "gdelt_conflict")
    return JSONResponse({"alerts": alerts, "total": len(alerts),
                         "degraded": len(alerts) == 0,
                         "_provenance": _provenance("gdelt_conflict")})


# ──────────────────────────────────────────────────────────────
# CATCH-ALL — unmapped endpoints return structured error
# ──────────────────────────────────────────────────────────────
@router.api_route("/api/{domain}/v1/{rpc}", methods=["POST", "GET", "OPTIONS"])
async def catch_all_rpc(domain: str, rpc: str, request: Request):
    if request.method == "OPTIONS":
        return _options_response()
    print(f"[WARN] Unmapped Globe API endpoint: /api/{domain}/v1/{rpc}")
    return JSONResponse(
        {"error": f"Endpoint /api/{domain}/v1/{rpc} not implemented.", "degraded": False, "data": []},
        status_code=200,
    )


print("🌍 [SPARK] Globe Intelligence API loaded — providers:", list(_CB.keys()))
