/**
 * Global Zustand store for SPARK Globe Monitor.
 * Features:
 *   - Time window filtering (1h / 6h / 24h / 48h / 7d)
 *   - Activity tracking: seenEventIds, newEventIds, per-panel change badges
 *   - Custom keyword monitors (user-defined, persistent, colored)
 *   - Layer visibility controls (20+ layer catalog)
 *   - Signal Fusion engine (correlations with confidence)
 *   - Investigation Case Drawer (cases + notes)
 *   - Snapshot metadata (actual data persisted in IndexedDB by useSnapshotStore)
 *   - Playback state (index into snapshot history)
 */
import { create } from 'zustand';
import { persist, subscribeWithSelector } from 'zustand/middleware';

// ── Core types ───────────────────────────────────────────────────────────────
export type MonitorMode = 'world' | 'tech' | 'finance' | 'happy';
export type Severity = 'low' | 'medium' | 'high' | 'critical';
export type TimeWindow = '1h' | '6h' | '24h' | '48h' | '7d';

// ── Layer catalog (expanded — 37 layers) ────────────────────────────────────
export const ALL_LAYERS = [
  // Geopolitical
  'conflict', 'displacement', 'cyber', 'government',
  // Natural hazards
  'earthquake', 'wildfire', 'climate', 'volcano', 'flood', 'storm', 'disease',
  // Infrastructure
  'flights', 'shipping', 'cables', 'pipelines', 'datacenter', 'infrastructure', 'power',
  // Economic
  'finance', 'crypto', 'energy', 'economy',
  // Environmental
  'airquality', 'radiation', 'deforestation',
  // Intelligence feeds
  'network', 'bgp', 'leaks', 'custom',
  // Space / special
  'satellites', 'solar',
  // Live news geo
  'news',
] as const;
export type LayerId = (typeof ALL_LAYERS)[number];

// ── Provenance metadata ─────────────────────────────────────────────────────
export interface Provenance {
  provider: string;       // Circuit-breaker key, e.g. "usgs"
  source: string;         // Human-readable name, e.g. "USGS GeoJSON Feed"
  sourceUrl: string;      // Canonical source URL
  retrievedAt: number;    // Unix milliseconds
  cacheAge: number;       // Seconds since last cache refresh
  retrievalMethod: string;// "http_cached" | "http_live" | "ws_push"
}

// ── Data interfaces ─────────────────────────────────────────────────────────
export interface ViewState {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
  transitionDuration: number;
}

/** Unified real-time event shape */
export interface RealEvent {
  id: string;
  title: string;
  location: string;
  lat: number;
  lng: number;
  severity: Severity;
  category: string;
  timestamp: 'today' | 'yesterday' | 'this_week';
  description: string;
  fetchedAt?: number; // unix ms — for time-window filtering
  _provenance?: Provenance;
}

export interface RealFireEvent {
  id: string;
  title: string;
  lat: number;
  lng: number;
  brightness: number;
  frp: number;
  fetchedAt?: number;
  _provenance?: Provenance;
}

export interface RealTicker {
  symbol: string;
  value: number;
  delta: number;
  deltaPercent: number;
  source?: string;
}

export interface GdeltArticle {
  title: string;
  url: string;
  source: string;
  date: string;
  image: string;
  language: string;
  tone: number;
}

// ── Custom monitors ──────────────────────────────────────────────────────────
export interface CustomMonitor {
  id: string;
  keyword: string;
  color: string;   // hex color
  enabled: boolean;
  createdAt: number;
  matchCount: number; // updated each fetch
}

// ── Signal Fusion ────────────────────────────────────────────────────────────
export interface FusionItem {
  id: string;
  title: string;
  summary: string;
  confidence: number; // 0–1
  evidenceLinks: string[];
  entities: string[];
  regions: string[];
  cause?: string;
  effect?: string;
  dataGaps: string[];
  severity: Severity;
  updatedAt: number;
}

// ── Provider health ─────────────────────────────────────────────────────────
export interface ProviderHealth {
  name: string;
  status: 'ok' | 'degraded' | 'down' | 'key_required';
  failureCount: number;
  lastOkAgo: number | null;   // seconds
  lastError: string;
  cooldownRemaining: number;  // seconds
}

// ── Cases ────────────────────────────────────────────────────────────────────
export interface CaseNote {
  id: string;
  content: string;
  createdAt: number;
}

export interface InvestigationCase {
  id: string;
  title: string;
  eventId: string;
  severity: Severity;
  category: string;
  notes: CaseNote[];
  linkedEventIds: string[];
  status: 'open' | 'monitoring' | 'closed';
  createdAt: number;
}

// ── Snapshot metadata (full data in IndexedDB) ────────────────────────────────
export interface SnapshotMeta {
  id: string;
  label: string;
  createdAt: number;
  eventCount: number;
  mode: MonitorMode;
}

// ── Main store interface ─────────────────────────────────────────────────────
export interface MonitorState {
  // ── Core
  mode: MonitorMode;
  viewState: ViewState;
  selectedEventId: string | null;

  // ── Time filtering
  timeWindow: TimeWindow;
  setTimeWindow: (tw: TimeWindow) => void;

  // ── Layer visibility
  visibleLayers: LayerId[];
  toggleLayer: (layer: LayerId) => void;
  setVisibleLayers: (layers: LayerId[]) => void;

  // ── AI Core
  aiCoreExpanded: boolean;
  aiMessages: { role: 'user' | 'ai'; content: string }[];

  // ── Panels
  leftPanelOpen: boolean;
  rightPanelOpen: boolean;
  intelPanelOpen: boolean;
  newsPanelOpen: boolean;
  fusionPanelOpen: boolean;
  caseDrawerOpen: boolean;

  // ── Real-time data
  realEvents: RealEvent[];
  realWorldEvents: RealEvent[];
  realCyberEvents: RealEvent[];
  realFinanceEvents: RealEvent[];
  newsGeoEvents: RealEvent[];
  realClimateEvents: RealEvent[];
  realFireEvents: RealFireEvent[];
  realMarketTickers: RealTicker[];
  gdeltArticles: GdeltArticle[];
  newsArticles: GdeltArticle[];
  intelTopic: string;
  dataLoading: boolean;
  newsLoading: boolean;
  intelLoading: boolean;
  lastFetch: number;

  // ── Activity tracking
  seenEventIds: string[];          // persisted: IDs already viewed
  newEventIds: string[];           // set on each fetch = incoming IDs not in seenEventIds
  markAsSeen: (ids: string[]) => void;

  // ── Custom monitors
  customMonitors: CustomMonitor[];
  addCustomMonitor: (keyword: string, color: string) => void;
  toggleCustomMonitor: (id: string) => void;
  removeCustomMonitor: (id: string) => void;
  updateCustomMonitorCount: (id: string, count: number) => void;

  // ── Provider health
  providerHealth: ProviderHealth[];
  providerHealthSummary: { ok: number; degraded: number; down: number; key_required: number; total: number } | null;
  fetchProviderHealth: () => Promise<void>;

  // ── WebSocket push (Globe /ws/globe)
  wsConnected: boolean;
  wsLastPush: number | null;
  setWsConnected: (connected: boolean) => void;
  mergeGlobeDelta: (layer: string, events: RealEvent[]) => void;
  setGlobeTickers: (tickers: RealTicker[]) => void;

  // ── Signal Fusion
  fusionItems: FusionItem[];
  fusionLoading: boolean;
  fetchFusionSummary: () => Promise<void>;

  // ── Cases
  cases: InvestigationCase[];
  addCase: (event: Pick<RealEvent, 'id' | 'title' | 'severity' | 'category'>) => void;
  removeCase: (id: string) => void;
  addCaseNote: (caseId: string, note: string) => void;
  updateCaseStatus: (caseId: string, status: InvestigationCase['status']) => void;
  linkEventToCase: (caseId: string, eventId: string) => void;

  // ── Snapshots
  snapshots: SnapshotMeta[];
  playbackIndex: number | null;   // null = live, number = snapshot index
  addSnapshotMeta: (meta: SnapshotMeta) => void;
  removeSnapshotMeta: (id: string) => void;
  setPlaybackIndex: (i: number | null) => void;

  // ── Map settings
  mapView: '2d' | '3d';
  setMapView: (view: '2d' | '3d') => void;
  mapStyle: 'dark' | 'street' | 'satellite';
  setMapStyle: (style: 'dark' | 'street' | 'satellite') => void;
  mapLabels: boolean;
  setMapLabels: (on: boolean) => void;

  // ── Actions
  setMode: (mode: MonitorMode) => void;
  flyTo: (lng: number, lat: number, zoom?: number) => void;
  selectEvent: (id: string | null) => void;
  toggleAICore: () => void;
  addAIMessage: (role: 'user' | 'ai', content: string) => void;
  toggleLeftPanel: () => void;
  toggleRightPanel: () => void;
  toggleIntelPanel: () => void;
  toggleNewsPanel: () => void;
  toggleFusionPanel: () => void;
  toggleCaseDrawer: () => void;
  setViewState: (vs: ViewState) => void;
  setIntelTopic: (topic: string) => void;
  fetchRealTimeData: () => Promise<void>;
  fetchGdeltIntel: (topic: string) => Promise<void>;
  fetchNews: (mode: MonitorMode) => Promise<void>;
  fetchNewsGeo: (mode: MonitorMode) => Promise<void>;
}

// ── Time-window helper: ms per window ────────────────────────────────────────
export const TIME_WINDOW_MS: Record<TimeWindow, number> = {
  '1h':  1 * 60 * 60 * 1000,
  '6h':  6 * 60 * 60 * 1000,
  '24h': 24 * 60 * 60 * 1000,
  '48h': 48 * 60 * 60 * 1000,
  '7d':  7 * 24 * 60 * 60 * 1000,
};

/** Default camera */
const DEFAULT_VIEW: ViewState = {
  longitude: 20,
  latitude: 25,
  zoom: 2.2,
  pitch: 35,
  bearing: 0,
  transitionDuration: 0,
};

const DEFAULT_VISIBLE_LAYERS: LayerId[] = [
  'conflict', 'earthquake', 'wildfire', 'climate', 'flights', 'custom', 'news',
];

const POST_JSON = (body: unknown) => ({
  method: 'POST',
  body: JSON.stringify(body),
  headers: { 'Content-Type': 'application/json' },
});

const safeFetch = async (url: string, init?: RequestInit) => {
  try {
    const r = await fetch(url, init);
    return r.ok ? r.json() : {};
  } catch {
    return {};
  }
};

// ── Store ────────────────────────────────────────────────────────────────────
export const useMonitorStore = create<MonitorState>()(
  persist(
    subscribeWithSelector((set, get) => ({
      // ── Core defaults
      mode: 'world',
      viewState: DEFAULT_VIEW,
      selectedEventId: null,

      // ── Time window
      timeWindow: '24h',
      setTimeWindow: (tw) => set({ timeWindow: tw }),

      // ── Layers
      visibleLayers: DEFAULT_VISIBLE_LAYERS,
      toggleLayer: (layer) =>
        set((s) => ({
          visibleLayers: s.visibleLayers.includes(layer)
            ? s.visibleLayers.filter((l) => l !== layer)
            : [...s.visibleLayers, layer],
        })),
      setVisibleLayers: (layers) => set({ visibleLayers: layers }),

      // ── AI Core
      aiCoreExpanded: false,
      aiMessages: [],

      // ── Panels
      leftPanelOpen: true,
      rightPanelOpen: true,
      intelPanelOpen: false,
      newsPanelOpen: false,
      fusionPanelOpen: false,
      caseDrawerOpen: false,

      // ── Data
      realEvents: [],
      realWorldEvents: [],
      realCyberEvents: [],
      realFinanceEvents: [],
      newsGeoEvents: [],
      realClimateEvents: [],
      realFireEvents: [],
      realMarketTickers: [],
      gdeltArticles: [],
      newsArticles: [],
      intelTopic: 'military',
      dataLoading: false,
      newsLoading: false,
      intelLoading: false,
      lastFetch: 0,

      // ── Activity tracking
      seenEventIds: [],
      newEventIds: [],
      markAsSeen: (ids) =>
        set((s) => ({
          seenEventIds: Array.from(new Set([...s.seenEventIds, ...ids])),
          newEventIds: s.newEventIds.filter((id) => !ids.includes(id)),
        })),

      // ── Custom monitors
      customMonitors: [],
      addCustomMonitor: (keyword, color) =>
        set((s) => ({
          customMonitors: [
            ...s.customMonitors,
            {
              id: `cm-${Date.now()}`,
              keyword: keyword.trim().toLowerCase(),
              color,
              enabled: true,
              createdAt: Date.now(),
              matchCount: 0,
            },
          ],
        })),
      toggleCustomMonitor: (id) =>
        set((s) => ({
          customMonitors: s.customMonitors.map((m) =>
            m.id === id ? { ...m, enabled: !m.enabled } : m
          ),
        })),
      removeCustomMonitor: (id) =>
        set((s) => ({
          customMonitors: s.customMonitors.filter((m) => m.id !== id),
        })),
      updateCustomMonitorCount: (id, count) =>
        set((s) => ({
          customMonitors: s.customMonitors.map((m) =>
            m.id === id ? { ...m, matchCount: count } : m
          ),
        })),

      // ── Provider health
      providerHealth: [],
      providerHealthSummary: null,
      fetchProviderHealth: async () => {
        const data = await safeFetch('/api/globe/v1/getProviderHealth');
        set({
          providerHealth: data.providers || [],
          providerHealthSummary: data.summary || null,
        });
      },

      // ── WebSocket push state
      wsConnected: false,
      wsLastPush: null,
      setWsConnected: (connected) => set({ wsConnected: connected }),
      mergeGlobeDelta: (layer, events) =>
        set((s) => {
          const now = Date.now();
          const incoming = events.map((e) => ({
            ...e,
            fetchedAt: e.fetchedAt ?? now,
            location:  e.location ?? '',
            timestamp: 'today' as const,
            description: e.description ?? '',
          }));
          const incoming_ids = new Set(incoming.map((e) => e.id));
          const existing = s.realEvents.filter(
            (e) => e.category !== layer || !incoming_ids.has(e.id)
          );
          return {
            realEvents: [...incoming, ...existing].slice(0, 500),
            wsLastPush: now,
          };
        }),
      setGlobeTickers: (tickers) => set({ realMarketTickers: tickers }),

      // ── Signal Fusion
      fusionItems: [],
      fusionLoading: false,
      fetchFusionSummary: async () => {
        set({ fusionLoading: true });
        const data = await safeFetch('/api/globe/v1/getFusionSummary', POST_JSON({}));
        set({
          fusionItems: data.items || [],
          fusionLoading: false,
        });
      },

      // ── Cases
      cases: [],
      addCase: (event) =>
        set((s) => {
          if (s.cases.some((c) => c.eventId === event.id)) return s;
          const now = Date.now();
          return {
            cases: [
              ...s.cases,
              {
                id: `case-${now}`,
                title: event.title,
                eventId: event.id,
                severity: event.severity,
                category: event.category,
                notes: [],
                linkedEventIds: [],
                status: 'open',
                createdAt: now,
              },
            ],
          };
        }),
      removeCase: (id) =>
        set((s) => ({ cases: s.cases.filter((c) => c.id !== id) })),
      addCaseNote: (caseId, note) =>
        set((s) => ({
          cases: s.cases.map((c) =>
            c.id === caseId
              ? {
                  ...c,
                  notes: [
                    ...c.notes,
                    { id: `note-${Date.now()}`, content: note, createdAt: Date.now() },
                  ],
                }
              : c
          ),
        })),
      updateCaseStatus: (caseId, status) =>
        set((s) => ({
          cases: s.cases.map((c) => (c.id === caseId ? { ...c, status } : c)),
        })),
      linkEventToCase: (caseId, eventId) =>
        set((s) => ({
          cases: s.cases.map((c) =>
            c.id === caseId && !c.linkedEventIds.includes(eventId)
              ? { ...c, linkedEventIds: [...c.linkedEventIds, eventId] }
              : c
          ),
        })),

      // ── Snapshots
      snapshots: [],
      playbackIndex: null,
      addSnapshotMeta: (meta) =>
        set((s) => ({ snapshots: [...s.snapshots.slice(-49), meta] })), // keep last 50
      removeSnapshotMeta: (id) =>
        set((s) => ({ snapshots: s.snapshots.filter((m) => m.id !== id) })),
      setPlaybackIndex: (i) => set({ playbackIndex: i }),

      // ── fetchRealTimeData ─────────────────────────────────────────────────
      fetchRealTimeData: async () => {
        set({ dataLoading: true });
        const now = Date.now();
        // Pass active layers so backend skips disabled layer fetches
        const { visibleLayers } = get();
        const layers = visibleLayers as string[];
        try {
          const [eqData, flightsData, conflictData, cyberData, financeData, marketData, firesData, climateData, newsGeoData] =
            await Promise.all([
              safeFetch('/api/seismology/v1/listEarthquakes',     POST_JSON({ layers })),
              safeFetch('/api/military/v1/listMilitaryFlights',   POST_JSON({ layers })),
              safeFetch('/api/conflict/v1/listConflictEvents',    POST_JSON({ layers })),
              safeFetch('/api/intelligence/v1/searchGdeltDocuments', POST_JSON({ topic: 'cyber',      maxRecords: 20 })),
              safeFetch('/api/intelligence/v1/searchGdeltDocuments', POST_JSON({ topic: 'sanctions',  maxRecords: 20 })),
              safeFetch('/api/market/v1/getTicker',               POST_JSON({ layers })),
              safeFetch('/api/wildfire/v1/listFireDetections',    POST_JSON({ layers })),
              safeFetch('/api/climate/v1/listClimateAnomalies',   POST_JSON({ layers })),
              safeFetch('/api/news/v1/listNewsGeo',               POST_JSON({ mode: get().mode })),
            ]);

          const realEarthquakes: RealEvent[] = (eqData.earthquakes || []).map((eq: any) => ({
            id: eq.id,
            title: `M${Number(eq.magnitude).toFixed(1)} – ${eq.place}`,
            location: eq.place || 'Unknown',
            lat: eq.location?.latitude || 0,
            lng: eq.location?.longitude || 0,
            severity: eq.severity || ((eq.magnitude >= 7 ? 'critical' : eq.magnitude >= 6 ? 'high' : 'medium') as Severity),
            category: 'earthquake',
            timestamp: 'today',
            description: `Depth: ${Number(eq.depthKm || 0).toFixed(0)} km`,
            fetchedAt: now,
          }));

          const realFlights: RealEvent[] = (flightsData.flights || [])
            .filter((f: any) => f.location?.latitude && f.location?.longitude)
            .map((f: any) => ({
              id: f.hexCode,
              title: `${f.type || 'Military Aircraft'} ${f.registration}`,
              location: 'Airspace',
              lat: f.location.latitude,
              lng: f.location.longitude,
              severity: 'high' as Severity,
              category: 'flights',
              timestamp: 'today',
              description: `Alt: ${Number(f.altitudeFeet || 0).toFixed(0)} ft`,
              fetchedAt: now,
            }));

          const realWorldEvents: RealEvent[] = (conflictData.events || []).map((e: any) => ({
            id: e.id || Math.random().toString(36).slice(2),
            title: e.title || 'Conflict Event',
            location: e.location || 'Unknown',
            lat: e.lat || 0,
            lng: e.lng || 0,
            severity: (e.severity as Severity) || 'high',
            category: e.category || 'conflict',
            timestamp: 'today',
            description: e.description || e.domain || 'GDELT Intelligence',
            fetchedAt: now,
          }));

          const realCyberEvents: RealEvent[] = (cyberData.articles || []).map((a: any, i: number) => ({
            id: `cyber-${i}`,
            title: a.title || 'Cyber Event',
            location: a.source || 'Unknown',
            lat: 0,
            lng: 0,
            severity: (a.tone < -8 ? 'critical' : a.tone < -4 ? 'high' : 'medium') as Severity,
            category: 'cyber',
            timestamp: 'today',
            description: a.source || '',
            fetchedAt: now,
          }));

          const realFinanceEvents: RealEvent[] = (financeData.articles || []).map((a: any, i: number) => ({
            id: `fin-${i}`,
            title: a.title || 'Market Event',
            location: a.source || 'Global Markets',
            lat: 0,
            lng: 0,
            severity: (a.tone < -8 ? 'critical' : a.tone < -4 ? 'high' : 'medium') as Severity,
            category: 'economic',
            timestamp: 'today',
            description: a.source || '',
            fetchedAt: now,
          }));

          const realMarketTickers: RealTicker[] = (marketData.tickers || []);

          const realFireEvents: RealFireEvent[] = (firesData.fireDetections || []).map((f: any) => ({
            id: f.id || Math.random().toString(36).slice(2),
            title: f.title || 'Wildfire',
            lat: f.lat || 0,
            lng: f.lon || 0,
            brightness: f.brightness || 400,
            frp: f.frp || 0,
            fetchedAt: now,
          })).filter((f: RealFireEvent) => f.lat !== 0 && f.lng !== 0);

          const realClimateEvents: RealEvent[] = (climateData.anomalies || [])
            .filter((a: any) => a.lat && a.lng)
            .map((a: any) => ({
              id: a.id || Math.random().toString(36).slice(2),
              title: a.title,
              location: a.categoryLabel || 'Natural Event',
              lat: a.lat,
              lng: a.lng,
              severity: (a.severity as Severity) || 'medium',
              category: a.category || 'climate',
              timestamp: 'today',
              description: a.categoryLabel || '',
              fetchedAt: now,
            }));

          const newsGeoEvents: RealEvent[] = (newsGeoData.events || [])
            .filter((e: any) => e.lat && e.lng)
            .map((e: any) => ({
              id:          e.id || Math.random().toString(36).slice(2),
              title:       e.title || 'World News',
              location:    e.location || 'Unknown',
              lat:         e.lat,
              lng:         e.lng,
              severity:    (e.severity as Severity) || 'medium',
              category:    'news',
              timestamp:   'today' as const,
              description: e.source || 'GDELT',
              fetchedAt:   now,
            }));

          // ── Activity tracking: find NEW events ──────────────────────────
          const incomingIds = [
            ...realEarthquakes.map((e) => e.id),
            ...realFlights.map((e) => e.id),
            ...realWorldEvents.map((e) => e.id),
          ];
          const { seenEventIds } = get();
          const newEventIds = incomingIds.filter((id) => !seenEventIds.includes(id));

          // ── Custom monitor matching ─────────────────────────────────────
          const { customMonitors } = get();
          const allArticleTitles = [
            ...realWorldEvents.map((e) => e.title),
            ...realCyberEvents.map((e) => e.title),
            ...realFinanceEvents.map((e) => e.title),
          ];
          customMonitors.forEach((m) => {
            if (!m.enabled) return;
            const count = allArticleTitles.filter((t) =>
              t.toLowerCase().includes(m.keyword)
            ).length;
            if (count !== m.matchCount) get().updateCustomMonitorCount(m.id, count);
          });

          set({
            realEvents:        [...realEarthquakes, ...realFlights],
            realWorldEvents,
            realCyberEvents,
            realFinanceEvents,
            realClimateEvents,
            realFireEvents,
            realMarketTickers,
            newsGeoEvents,
            dataLoading: false,
            lastFetch: now,
            newEventIds,
          });
        } catch (err) {
          console.error('[SPARK] fetchRealTimeData error:', err);
          set({ dataLoading: false });
        }
      },

      // ── fetchGdeltIntel ───────────────────────────────────────────────────
      fetchGdeltIntel: async (topic: string) => {
        set({ intelTopic: topic, intelLoading: true });
        const data = await safeFetch('/api/intelligence/v1/searchGdeltDocuments', POST_JSON({ topic, maxRecords: 25 }));
        set({ gdeltArticles: data.articles || [], intelLoading: false });
      },

      // ── fetchNews ─────────────────────────────────────────────────────────
      fetchNews: async (mode: MonitorMode) => {
        set({ newsLoading: true });
        const data = await safeFetch('/api/news/v1/listNewsArticles', POST_JSON({ mode }));
        set({ newsArticles: data.articles || [], newsLoading: false });
      },

      // ── fetchNewsGeo ──────────────────────────────────────────────────────
      // Geo-tagged news for globe map overlay (GDELT artgeo mode)
      fetchNewsGeo: async (mode: MonitorMode) => {
        const now = Date.now();
        const data = await safeFetch('/api/news/v1/listNewsGeo', POST_JSON({ mode }));
        const newsGeoEvents: RealEvent[] = (data.events || []).map((e: any) => ({
          id:          e.id,
          title:       e.title,
          location:    e.location || 'Unknown',
          lat:         e.lat,
          lng:         e.lng,
          severity:    e.severity || 'medium',
          category:    'news',
          timestamp:   'today' as const,
          description: e.source || 'GDELT News',
          fetchedAt:   now,
        }));
        set({ newsGeoEvents });
      },

      // ── Map settings
      mapView: '3d',
      setMapView: (view) => set({ mapView: view }),
      mapStyle: 'dark',
      setMapStyle: (style) => set({ mapStyle: style }),
      mapLabels: true,
      setMapLabels: (on) => set({ mapLabels: on }),

      // ── Standard actions ──────────────────────────────────────────────────
      setMode: (mode) => {
        set({ mode, selectedEventId: null });
        get().fetchNews(mode);
        get().fetchNewsGeo(mode);
      },
      flyTo: (longitude, latitude, zoom = 5) =>
        set({ viewState: { longitude, latitude, zoom, pitch: 45, bearing: 0, transitionDuration: 2000 } }),
      selectEvent: (id) => set({ selectedEventId: id }),
      toggleAICore: () => set((s) => ({ aiCoreExpanded: !s.aiCoreExpanded })),
      addAIMessage: (role, content) =>
        set((s) => ({ aiMessages: [...s.aiMessages, { role, content }] })),
      toggleLeftPanel:   () => set((s) => ({ leftPanelOpen:   !s.leftPanelOpen })),
      toggleRightPanel:  () => set((s) => ({ rightPanelOpen:  !s.rightPanelOpen })),
      toggleIntelPanel:  () => set((s) => ({ intelPanelOpen:  !s.intelPanelOpen })),
      toggleNewsPanel:   () => set((s) => ({ newsPanelOpen:   !s.newsPanelOpen })),
      toggleFusionPanel: () => set((s) => ({ fusionPanelOpen: !s.fusionPanelOpen })),
      toggleCaseDrawer:  () => set((s) => ({ caseDrawerOpen:  !s.caseDrawerOpen })),
      setViewState: (vs) => set({ viewState: { ...vs, transitionDuration: 0 } }),
      setIntelTopic: (topic) => get().fetchGdeltIntel(topic),
    })),
    {
      name: 'spark-monitor-v2',
      // Only persist user preferences and cases — NOT live data
      partialize: (s) => ({
        mode:          s.mode,
        timeWindow:    s.timeWindow,
        visibleLayers: s.visibleLayers,
        seenEventIds:  s.seenEventIds.slice(-2000), // cap to 2000
        customMonitors: s.customMonitors,
        cases:         s.cases,
        snapshots:     s.snapshots,
        leftPanelOpen:  s.leftPanelOpen,
        rightPanelOpen: s.rightPanelOpen,
        mapView:        s.mapView,
        mapStyle:       s.mapStyle,
        mapLabels:      s.mapLabels,
      }),
    }
  )
);
