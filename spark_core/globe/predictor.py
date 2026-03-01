"""
SPARK Globe Threat Predictor
Probabilistic risk scoring & event escalation modeling for Globe Monitor.

Analyzes real-time event streams and produces:
  - Per-region risk scores (0–100)
  - Escalation vectors (what could trigger next)
  - Cluster alerts (event density → hotspot detection)
  - Trend analysis (is a region getting worse / better?)
  - Probabilistic "if X → then Y" simulations

No external ML dependency required — uses statistical heuristics
that work reliably on real event data from GDELT/ACLED/USGS.
"""
import math
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class ThreatEvent:
    event_id: str
    lat: float
    lng: float
    event_type: str      # "conflict" | "earthquake" | "fire" | "cyber" | "sanctions"
    severity: float      # 0.0–1.0
    source: str
    title: str
    timestamp: float
    region: Optional[str] = None
    country: Optional[str] = None
    tone: float = 0.0    # GDELT tone: negative = bad news


@dataclass
class RegionRisk:
    region_id: str       # e.g. "Eastern Europe", lat/lng grid cell
    risk_score: float    # 0–100
    risk_level: str      # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    dominant_threat: str
    event_count: int
    trend: str           # "RISING" | "STABLE" | "DECLINING"
    escalation_vectors: List[str] = field(default_factory=list)
    hotspot: bool = False
    lat: float = 0.0
    lng: float = 0.0
    computed_at: float = field(default_factory=time.time)


@dataclass
class EscalationScenario:
    trigger: str
    consequence: str
    probability: float   # 0–1
    timeframe: str       # "hours" | "days" | "weeks"
    affected_region: str
    risk_delta: float    # how much risk score would increase


# ── Constants ─────────────────────────────────────────────────────────────────

_TYPE_BASE_SEVERITY = {
    "conflict":    0.70,
    "earthquake":  0.60,
    "fire":        0.40,
    "cyber":       0.55,
    "sanctions":   0.35,
    "climate":     0.30,
    "news":        0.20,
}

_ESCALATION_RULES = [
    {
        "if_type": "conflict", "if_country": None, "if_severity_gte": 0.7,
        "then": "Risk of regional military escalation or refugee crisis within days.",
        "probability": 0.35, "timeframe": "days", "risk_delta": 15.0,
    },
    {
        "if_type": "earthquake", "if_country": None, "if_severity_gte": 0.8,
        "then": "Secondary disaster (landslide, tsunami Watch) possible within hours.",
        "probability": 0.25, "timeframe": "hours", "risk_delta": 20.0,
    },
    {
        "if_type": "cyber", "if_country": None, "if_severity_gte": 0.6,
        "then": "Critical infrastructure attack may follow reconnaissance activity.",
        "probability": 0.30, "timeframe": "weeks", "risk_delta": 12.0,
    },
    {
        "if_type": "sanctions", "if_country": None, "if_severity_gte": 0.5,
        "then": "Economic retaliation or proxy conflict response likely.",
        "probability": 0.40, "timeframe": "weeks", "risk_delta": 10.0,
    },
    {
        "if_type": "fire", "if_country": None, "if_severity_gte": 0.7,
        "then": "Air quality emergency and potential evacuation orders imminent.",
        "probability": 0.60, "timeframe": "hours", "risk_delta": 8.0,
    },
]

# Grid cell size for clustering
_GRID_DEGREES = 5.0   # 5° lat/lng ≈ 550 km


class ThreatPredictor:
    """
    Stateful threat prediction engine.
    Call `ingest(events)` whenever new data arrives.
    Call `get_region_risks()` for current risk map.
    """

    def __init__(self, history_window_s: int = 3600):
        """
        history_window_s: How long to keep events in rolling window (default 1 hour).
        """
        self._window = history_window_s
        self._events: List[ThreatEvent] = []
        self._region_cache: Dict[str, RegionRisk] = {}
        self._cache_ts: float = 0.0
        self._cache_ttl: float = 30.0   # recompute at most every 30s

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def ingest(self, raw_events: List[Dict[str, Any]], event_type: str = "conflict"):
        """
        Accept raw event dicts from globe_api and convert to ThreatEvents.
        """
        now = time.time()
        cutoff = now - self._window

        # Prune old events
        self._events = [e for e in self._events if e.timestamp > cutoff]

        for raw in raw_events:
            try:
                ev = self._parse_event(raw, event_type)
                if ev:
                    self._events.append(ev)
            except Exception:
                continue

        # Invalidate cache
        self._cache_ts = 0.0

    def _parse_event(self, raw: Dict[str, Any], default_type: str) -> Optional[ThreatEvent]:
        lat = float(raw.get("lat", raw.get("latitude", 0)) or 0)
        lng = float(raw.get("lng", raw.get("longitude", 0)) or 0)
        if lat == 0 and lng == 0:
            return None

        mag_raw   = raw.get("magnitude", raw.get("frp", raw.get("intensity", 0.5)))
        try:
            magnitude = float(mag_raw or 0)
        except Exception:
            magnitude = 0.5

        # Normalize magnitude to 0–1
        event_type = raw.get("type", default_type).lower()
        if event_type == "earthquake":
            severity = min(max((magnitude - 3.0) / 6.0, 0.0), 1.0)   # 3–9 Richter
        elif event_type == "fire":
            severity = min(magnitude / 1000.0, 1.0)                    # FRP in MW
        else:
            severity = float(raw.get("severity", raw.get("score",
                             _TYPE_BASE_SEVERITY.get(event_type, 0.5))))
            severity = min(max(severity, 0.0), 1.0)

        tone = float(raw.get("tone", 0.0))

        return ThreatEvent(
            event_id=str(raw.get("id", raw.get("event_id", id(raw)))),
            lat=lat, lng=lng,
            event_type=event_type,
            severity=severity,
            source=raw.get("source", "unknown"),
            title=str(raw.get("title", raw.get("event", "Event"))),
            timestamp=float(raw.get("timestamp", time.time())),
            region=raw.get("region", raw.get("country", None)),
            country=raw.get("country", None),
            tone=tone,
        )

    # ── Risk computation ──────────────────────────────────────────────────────

    def get_region_risks(self) -> List[RegionRisk]:
        """Return risk assessment for all active regions."""
        now = time.time()
        if now - self._cache_ts < self._cache_ttl and self._region_cache:
            return list(self._region_cache.values())

        # Group events by grid cell
        grid: Dict[str, List[ThreatEvent]] = defaultdict(list)
        for ev in self._events:
            cell = self._grid_cell(ev.lat, ev.lng)
            grid[cell].append(ev)

        new_cache: Dict[str, RegionRisk] = {}
        for cell, events in grid.items():
            risk = self._compute_cell_risk(cell, events)
            new_cache[cell] = risk

        self._region_cache = new_cache
        self._cache_ts = now
        return list(new_cache.values())

    def _grid_cell(self, lat: float, lng: float) -> str:
        cell_lat = math.floor(lat / _GRID_DEGREES) * _GRID_DEGREES
        cell_lng = math.floor(lng / _GRID_DEGREES) * _GRID_DEGREES
        return f"{cell_lat:.0f}_{cell_lng:.0f}"

    def _cell_center(self, cell: str) -> Tuple[float, float]:
        parts = cell.split("_")
        if len(parts) >= 2:
            try:
                lat = float(parts[0]) + _GRID_DEGREES / 2
                lng = float(parts[1]) + _GRID_DEGREES / 2
                return lat, lng
            except ValueError:
                pass
        return 0.0, 0.0

    def _compute_cell_risk(self, cell: str, events: List[ThreatEvent]) -> RegionRisk:
        if not events:
            lat, lng = self._cell_center(cell)
            return RegionRisk(
                region_id=cell, risk_score=0, risk_level="LOW",
                dominant_threat="none", event_count=0, trend="STABLE",
                lat=lat, lng=lng,
            )

        # Weighted severity sum
        weighted_sum = sum(
            ev.severity * _TYPE_BASE_SEVERITY.get(ev.event_type, 0.5) * 100
            for ev in events
        )
        density_factor = math.log1p(len(events)) / math.log1p(10)  # normalize
        raw_score = min(weighted_sum * density_factor / max(len(events), 1), 100.0)

        # Tone adjustment (negative tone → boost risk)
        avg_tone = sum(ev.tone for ev in events) / len(events)
        tone_adj = max(0, -avg_tone / 10.0) * 10  # maps -10 tone → +10 score
        risk_score = min(raw_score + tone_adj, 100.0)

        # Dominant threat
        type_counts: Dict[str, int] = defaultdict(int)
        for ev in events:
            type_counts[ev.event_type] += 1
        dominant = max(type_counts, key=type_counts.get)

        # Risk level
        if risk_score >= 70:
            level = "CRITICAL"
        elif risk_score >= 50:
            level = "HIGH"
        elif risk_score >= 30:
            level = "MEDIUM"
        else:
            level = "LOW"

        # Trend: compare recent half vs older half
        mid = len(events) // 2
        if mid > 0:
            older_avg = sum(e.severity for e in events[:mid]) / mid
            newer_avg = sum(e.severity for e in events[mid:]) / max(len(events) - mid, 1)
            delta = newer_avg - older_avg
            trend = "RISING" if delta > 0.05 else ("DECLINING" if delta < -0.05 else "STABLE")
        else:
            trend = "STABLE"

        # Hotspot: high density + high risk
        hotspot = len(events) >= 3 and risk_score >= 50

        # Escalation vectors
        escalations = self._compute_escalations(events)

        lat, lng = self._cell_center(cell)
        return RegionRisk(
            region_id=cell,
            risk_score=round(risk_score, 1),
            risk_level=level,
            dominant_threat=dominant,
            event_count=len(events),
            trend=trend,
            escalation_vectors=[e.consequence for e in escalations],
            hotspot=hotspot,
            lat=lat,
            lng=lng,
        )

    def _compute_escalations(self, events: List[ThreatEvent]) -> List[EscalationScenario]:
        scenarios = []
        max_by_type: Dict[str, ThreatEvent] = {}
        for ev in events:
            if ev.event_type not in max_by_type or ev.severity > max_by_type[ev.event_type].severity:
                max_by_type[ev.event_type] = ev

        for rule in _ESCALATION_RULES:
            ev = max_by_type.get(rule["if_type"])
            if ev and ev.severity >= rule["if_severity_gte"]:
                region = ev.region or ev.country or "this region"
                scenarios.append(EscalationScenario(
                    trigger=f"{rule['if_type'].title()} event (severity={ev.severity:.2f})",
                    consequence=rule["then"],
                    probability=rule["probability"],
                    timeframe=rule["timeframe"],
                    affected_region=region,
                    risk_delta=rule["risk_delta"],
                ))
        return scenarios

    # ── Global summary ────────────────────────────────────────────────────────

    def get_global_threat_summary(self) -> Dict[str, Any]:
        risks = self.get_region_risks()
        if not risks:
            return {
                "global_risk_score": 0,
                "global_risk_level": "LOW",
                "total_events": 0,
                "hotspots": 0,
                "critical_regions": [],
                "top_threats": [],
            }

        avg_score = sum(r.risk_score for r in risks) / len(risks)
        critical = [r for r in risks if r.risk_level == "CRITICAL"]
        high     = [r for r in risks if r.risk_level == "HIGH"]
        hotspots = sum(1 for r in risks if r.hotspot)

        # Global level
        if avg_score >= 60 or len(critical) >= 3:
            global_level = "CRITICAL"
        elif avg_score >= 40 or len(critical) >= 1:
            global_level = "HIGH"
        elif avg_score >= 20:
            global_level = "MEDIUM"
        else:
            global_level = "LOW"

        top_threats = sorted(risks, key=lambda r: r.risk_score, reverse=True)[:5]

        return {
            "global_risk_score": round(avg_score, 1),
            "global_risk_level": global_level,
            "total_events": sum(r.event_count for r in risks),
            "active_regions": len(risks),
            "hotspots": hotspots,
            "critical_count": len(critical),
            "high_count": len(high),
            "critical_regions": [
                {"region": r.region_id, "score": r.risk_score, "threat": r.dominant_threat,
                 "lat": r.lat, "lng": r.lng}
                for r in critical
            ],
            "top_threats": [
                {
                    "region": r.region_id,
                    "score": r.risk_score,
                    "level": r.risk_level,
                    "dominant_threat": r.dominant_threat,
                    "trend": r.trend,
                    "events": r.event_count,
                    "hotspot": r.hotspot,
                    "escalation_vectors": r.escalation_vectors[:2],
                    "lat": r.lat,
                    "lng": r.lng,
                }
                for r in top_threats
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        return {
            "tracked_events": len(self._events),
            "active_regions": len(self._region_cache),
            "window_s": self._window,
        }


# ── Singleton ─────────────────────────────────────────────────────────────────
threat_predictor = ThreatPredictor(history_window_s=3600)
