# SPARK Feature Matrix

> **Rule**: A feature is only marked ✅ Done when it has a backend endpoint, persistence strategy (if applicable), and a wired frontend component. Anything else is 🔧 Partial or ❌ Missing.

Last updated: 2026-03-01

---

## Legend

| Symbol | Meaning |
|--------|---------|
| ✅ | Fully wired end-to-end |
| 🔧 | Partially implemented (gap noted) |
| ❌ | UI / plan only — backend missing |
| 🚫 | Not planned yet |

---

## Core AI Chat

| Feature | Backend Endpoint | DB / Persistence | Frontend Component | Status |
|---------|-----------------|------------------|--------------------|--------|
| Send prompt → streaming tokens | `POST /ws/ai` (WS) | session memory (Chroma) | `Index.tsx` AI panel | ✅ |
| Cancel generation | `CANCEL` WS frame | — | Cancel button | ✅ |
| Tool execution reflection in HUD | `TOOL_EXECUTE` / `TOOL_RESULT` WS frames | — | HUD token stream | 🔧 Frontend listens but no dedicated HUD tile |
| Tool confirmation prompt | `CONFIRM_TOOL` via `/ws/system` | — | System channel handler | ✅ |
| Session history / recall | ChromaDB `session_memory.py` | Chroma `spark_memory_db/` | — | 🔧 Backend stored, no frontend history browser |

---

## Globe Intelligence Monitor

| Feature | Backend Endpoint | DB / Persistence | Frontend Component | Status |
|---------|-----------------|------------------|--------------------|--------|
| Earthquake layer | `GET /api/seismology/v1/listEarthquakes` | in-memory + 5 min TTL | GlobeMonitor layer toggle | ✅ |
| Conflict events | `GET /api/conflict/v1/listConflictEvents` | in-memory + TTL | GlobeMonitor layer toggle | ✅ |
| Wildfire detections | `GET /api/wildfire/v1/listFireDetections` | in-memory + TTL (NASA FIRMS) | GlobeMonitor layer toggle | ✅ |
| Market tickers | `GET /api/market/v1/marketSnapshot` | in-memory + TTL | GlobeMonitor ticker bar | ✅ |
| Live news panel | `GET /api/news/v1/listArticles` (GDELT) | in-memory + 300 s TTL | LiveNewsPanel | ✅ (429 stale-on-error fallback) |
| Signal Fusion panel | `GET /api/intelligence/v1/fusionSummary` | in-memory | FusionPanel | ✅ |
| Provider health panel | `GET /api/health` + `/api/config/status` | — | ProviderHealth UI | 🔧 `/api/config/status` new, UI not yet wired |
| Layer toggles persisted | — | ❌ no persistence | Layer toggle state | ❌ State lost on reload |
| **Case / Incident save** | `POST /api/globe/cases` | SQLite `cases.db` | CaseDrawer.tsx | ✅ (wired in this session) |
| Case list & delete | `GET /api/globe/cases` / `DELETE /api/globe/cases/{id}` | SQLite | CaseDrawer list view | ✅ (wired in this session) |
| Snapshot (export) | — | IndexedDB (frontend) | Snapshot button | 🔧 Frontend only, no backend export |

---

## System Telemetry (/ws/system)

| Feature | Backend Endpoint | DB / Persistence | Frontend Component | Status |
|---------|-----------------|------------------|--------------------|--------|
| CPU / RAM / disk stream | `/ws/system` STATE_UPDATE | — | SystemMetrics panel | ✅ (contract-aligned this session) |
| GPU stats | `/ws/system` (gpu_stats field) | — | SystemMetrics panel | 🔧 GPUtil optional, fallback = disk% |
| Network throughput | `/ws/system` (net_io field) | — | SystemMetrics panel | ✅ |
| Battery / charging | `/ws/system` payload | — | Battery indicator | ✅ |
| WS heartbeat / reconnect | `/ws/system` PING → PONG | — | `useSystemMetrics.ts` | ✅ (added this session) |
| Cognitive loop alerts pushed | `spark_alert` event bus → `/ws/system` ALERT frame | — | (needs frontend alert toast) | 🔧 Backend wired, no frontend ALERT handler yet |

---

## Cognitive / AI OS

| Feature | Backend Endpoint | DB / Persistence | Frontend Component | Status |
|---------|-----------------|------------------|--------------------|--------|
| Multi-agent status | `GET /api/agents/status` | — | CognitiveDashboard.tsx | ✅ |
| Dispatch task to agent | `POST /api/agents/dispatch` | — | CognitiveDashboard | ✅ |
| Natural-language agent ask | `POST /api/agents/ask` | — | CognitiveDashboard | ✅ |
| Model router status | `GET /api/models/status` | — | CognitiveDashboard | ✅ |
| Cognitive loop status | `GET /api/cognitive/status` | — | CognitiveDashboard | ✅ |
| Inject observation | `POST /api/cognitive/inject` | — | — | ✅ |
| Knowledge graph stats | `GET /api/memory/stats` | SQLite `knowledge_graph.db` | CognitiveDashboard | ✅ |
| Memory search | `GET /api/memory/search` | SQLite | — | ✅ backend only |
| Self-evolution proposals | `GET /api/evolution/proposals` | `evolution_log.jsonl` | CognitiveDashboard | ✅ (view only) |
| Approve / reject proposal | `POST /api/evolution/proposals/{id}/approve\|reject` | jsonl | CognitiveDashboard | 🔧 Backend ✅, frontend approve button missing |
| Trigger self-analysis | `POST /api/evolution/analyze` | — | — | ✅ backend only |
| Full OS snapshot | `GET /api/os/status` | — | CognitiveDashboard | ✅ |

---

## Threat Intelligence

| Feature | Backend Endpoint | DB / Persistence | Frontend Component | Status |
|---------|-----------------|------------------|--------------------|--------|
| Global threat summary | `GET /api/threat/summary` | in-memory (1h window) | CognitiveDashboard | ✅ |
| Per-region risk scores | `GET /api/threat/regions` | in-memory | CognitiveDashboard | ✅ |
| Feed custom events | `POST /api/threat/ingest` | in-memory | — | ✅ API only |

---

## Desktop Agent (spark_agent)

| Feature | Backend Endpoint | DB / Persistence | Frontend Component | Status |
|---------|-----------------|------------------|--------------------|--------|
| Open application | `POST http://127.0.0.1:7700/agent/open-app` | — | — | ✅ (added this session) |
| Open URL in browser | `POST http://127.0.0.1:7700/agent/open-url` | — | — | ✅ (added this session) |
| Run terminal command | `POST http://127.0.0.1:7700/agent/run-command` | audit log jsonl | — | ✅ (added this session) |
| File search in workspace | 🚫 | — | — | 🚫 planned |
| Create folder / file | 🚫 | — | — | 🚫 planned |
| UI automation (pyautogui) | 🚫 | — | — | 🚫 future |
| Screenshot capture | 🚫 | — | — | 🚫 future |

---

## Authentication

| Feature | Backend Endpoint | DB / Persistence | Frontend Component | Status |
|---------|-----------------|------------------|--------------------|--------|
| Login (bcrypt + JWT) | `POST /api/auth/login` | config/secrets.yaml | — | 🔧 backend ✅, no login UI page |
| Refresh token | `POST /api/auth/refresh` | in-memory revocation set | — | ✅ backend |
| Logout / revoke | `POST /api/auth/logout` | — | — | ✅ backend |
| List users (ADMIN) | `GET /api/auth/users` | secrets.yaml | — | ✅ backend |
| Create user (ROOT) | `POST /api/auth/users` | secrets.yaml | — | ✅ backend |

---

## API Infrastructure

| Feature | Endpoint | Status |
|---------|----------|--------|
| Version info | `GET /api/version` | ✅ (added this session) |
| Config / provider status | `GET /api/config/status` | ✅ (added this session) |
| Health liveness | `GET /api/health` | ✅ |
| Runtime diagnostics | `GET /api/health/runtime` | ✅ |
| API contract models (Pydantic) | `spark_core/contracts/models.py` | ✅ (added this session) |
| API contract types (TypeScript) | `src/types/contracts.ts` | ✅ (expanded this session) |

---

## Packaging & Launch

| Feature | File | Status |
|---------|------|--------|
| Python deps pinned | `requirements.txt` | ✅ |
| Node deps managed | `package.json` | ✅ |
| One-command launch | `run_spark.bat` | ✅ (upgraded this session) |
| Env var template | `.env.example` | ✅ (updated this session) |
| Backend serves built frontend | `dist/` static mount in main.py | ✅ |
| PyInstaller single-exe | 🚫 | 🚫 future |
| Tauri / Electron wrapper | 🚫 | 🚫 future |

---

## Known Gaps (priority order)

1. **Login UI** — No frontend login page; JWT tokens not managed in browser storage.
2. **Layer-toggle persistence** — Globe layer state lost on reload (needs `localStorage` or `POST /api/user/prefs`).
3. **ALERT toast** — `/ws/system` now pushes `ALERT` frames but no frontend handler shows them.
4. **Approve/reject evolution proposals** — Button exists in CognitiveDashboard but triggers no API call.
5. **Snapshot export backend** — Frontend saves IndexedDB; no `GET /api/snapshot` for server-side export.
6. **Tool execution HUD tile** — `TOOL_EXECUTE` / `TOOL_RESULT` frames arrive but no dedicated live feed tile.
