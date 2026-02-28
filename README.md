# S.P.A.R.K — Systematic Predictive Analysis & Reasoning Kernel

An advanced, sovereign AI development environment with an **integrated Globe Intelligence Monitor** — built for operators who need both deep code intelligence and real-time situational awareness in a single HUD.

---

## What is SPARK Globe Monitor?

SPARK Globe Monitor is a **fully-independent, real-time geospatial intelligence HUD** built into SPARK. It is **not a wrapper, iframe, or fork of any external product** — it is a first-class SPARK module with its own FastAPI backend, WebSocket push layer, Signal Fusion engine, and investigation workflow.

### Key Differentiators

| Feature | SPARK Globe Monitor | Typical OSINT Dashboard |
|---|---|---|
| **Data push** | **WebSocket push** (`/ws/globe`) — server pushes deltas | Frontend polls every N seconds |
| **Provenance** | Every event: source URL, cache age, retrieval method | Events have no traceability |
| **Trust layer** | Circuit breakers per provider + degraded-mode UI | Silent empty responses on failure |
| **Fusion engine** | Cross-source causal correlation with confidence scores | Independent unrelated layers |
| **Investigation** | Case drawer + notes + status lifecycle | Read-only display |
| **AI integration** | SPARK AI copilot reasons over live globe events | No AI integration |

---

## Core Features

### Globe Intelligence Monitor

- **Real-time WebSocket push** — `/ws/globe` streams deltas the moment data changes
- **15+ data layers**: conflict, earthquake, wildfire, climate, flights, vessels, disease alerts, air quality, internet outages, economic indicators, BGP alerts
- **Signal Fusion engine** — correlates cross-source events, outputs causal chains with confidence
- **Case Drawer** — save investigations, attach notes, track status (open → monitoring → closed)
- **Provider health dashboard** — live circuit-breaker status per data source
- **Optional keyed providers** — richer data when keys configured (ACLED, Finnhub, EIA, FIRMS, Cloudflare, OpenSky)
- **Provenance on every marker** — source URL, cache age, retrieval method, fetch timestamp | URL share state | Snapshot + Playback

### AI Development HUD

- Live CPU/RAM/GPU/Network telemetry
- AI Chat with streaming responses and tool execution feedback
- Voice Engine: Wake-Word + STT (Whisper) + TTS

### Sovereign AI Backend

- Local-First AI: Ollama with cloud fallback (OpenAI / Anthropic / Gemini)
- WebSocket Streaming: `/ws/ai` · `/ws/system` · `/ws/globe`
- Tool Sandbox: Docker-isolated code execution
- Memory: persistent conversation + project context

---

## Directory Structure

```
S.P.A.R.K/
├── src/
│   ├── pages/WorldMonitor.tsx       # Globe HUD layout
│   ├── components/monitor/          # Globe components
│   │   ├── MapContainer.tsx         # DeckGL + MapLibre globe
│   │   ├── FusionPanel.tsx          # Signal Fusion
│   │   ├── CaseDrawer.tsx           # Investigation workflow
│   │   ├── ProviderHealthPanel.tsx  # Circuit-breaker status
│   │   ├── LayerTogglePanel.tsx     # 36-layer toggle
│   │   └── ProvenanceTooltip.tsx    # Event trust metadata
│   ├── store/useMonitorStore.ts     # Zustand global store
│   └── hooks/
│       ├── useGlobeSocket.ts        # WebSocket push consumer
│       ├── useUrlState.ts           # Hash share URLs
│       ├── useActivityTracker.ts    # NEW badge tracking
│       └── useSnapshotStore.ts      # IndexedDB snapshots
├── spark_core/
│   ├── main.py                      # FastAPI app + all WS endpoints
│   ├── globe_api.py                 # Globe Intelligence API
│   └── ws/manager.py                # WebSocket manager
├── audio/                           # STT / TTS / VAD / WakeWord
├── vision/                          # Computer Vision
└── config/                          # secrets.yaml
```

---

## Getting Started

### Prerequisites

| Component | Requirement |
|---|---|
| OS | Windows 10/11 or Linux |
| Python | 3.10+ |
| Node.js | v18+ |
| Docker | Docker Desktop (for code sandbox) |
| AI Model | [Ollama](https://ollama.com/) with llama3 or deepseek-r1 |

### Installation

```powershell
git clone https://github.com/itzmesooraj8/S.P.A.R.K.git
cd S.P.A.R.K
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
npm install
cp .env.example .env   # optional: add keys to unlock extra layers
```

### Running

```powershell
.\run_spark.bat          # automated (Windows)
# or manually:
python run_server.py     # backend  → http://localhost:8000
npm run dev              # frontend → http://localhost:8080
```

---

## Globe Intelligence API

The Globe Monitor works **fully without any API keys**. Keys unlock richer providers:

| Key | Unlocks |
|---|---|
| `ACLED_ACCESS_TOKEN` + `ACLED_EMAIL` | Geocoded conflict events with fatality counts |
| `FINNHUB_API_KEY` | SPY/QQQ/GLD/OIL real-time stock quotes |
| `EIA_API_KEY` | WTI crude oil price |
| `NASA_FIRMS_API_KEY` | High-res VIIRS satellite fire detections |
| `CLOUDFLARE_API_TOKEN` | Internet outage layer |
| `OPENSKY_CLIENT_ID/SECRET` | Higher flight tracking rate limits |

---

## WebSocket Protocol

### `/ws/globe` — Globe Push

Server pushes event deltas whenever data refreshes:

```json
{ "type": "GLOBE_DELTA",  "layer": "earthquake", "events": [...], "timestamp": 1234567890 }
{ "type": "GLOBE_TICKER", "tickers": [...],       "timestamp": 1234567890 }
{ "type": "GLOBE_FUSION", "items": [...],          "timestamp": 1234567890 }
{ "type": "GLOBE_HEALTH", "providers": [...],      "summary": {...} }
```

Every event includes provenance:

```json
{
  "id": "us7000abc",
  "title": "M6.2 — Southern Japan",
  "lat": 34.5, "lng": 135.1,
  "severity": "high",
  "_provenance": {
    "source": "USGS GeoJSON Feed",
    "provider": "usgs",
    "retrievedAt": 1740700000000,
    "cacheAge": 45,
    "retrievalMethod": "http_cached",
    "sourceUrl": "https://earthquake.usgs.gov/earthquakes/..."
  }
}
```

---

## REST API

Interactive docs: `http://localhost:8000/docs`

```
POST /api/seismology/v1/listEarthquakes
POST /api/conflict/v1/listConflictEvents
POST /api/military/v1/listMilitaryFlights
POST /api/wildfire/v1/listFireDetections
POST /api/climate/v1/listClimateAnomalies
POST /api/market/v1/getTicker
POST /api/intelligence/v1/searchGdeltDocuments
POST /api/news/v1/listNewsArticles
POST /api/health/v1/listDiseaseAlerts
POST /api/airquality/v1/listAirQualityAlerts
POST /api/shipping/v1/listVesselAlerts
POST /api/economy/v1/getEconomicIndicators
POST /api/bgp/v1/listNetworkAlerts
GET  /api/globe/v1/getProviderHealth
POST /api/globe/v1/getFusionSummary
```

---

## License

MIT — see [LICENSE](LICENSE)
