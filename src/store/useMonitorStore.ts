/**
 * Global Zustand store for World Monitor V2.
 * Manages monitor mode, map view state, AI copilot, panel visibility,
 * and ALL real-time data feeds (earthquakes, conflicts, fires, market, GDELT intel).
 */
import { create } from 'zustand';

export type MonitorMode = 'world' | 'tech' | 'finance' | 'happy';
export type Severity = 'low' | 'medium' | 'high' | 'critical';

export interface ViewState {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
  transitionDuration: number;
}

/** Unified real-time event shape (matches mock MonitorEvent structure) */
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
}

export interface RealFireEvent {
  id: string;
  title: string;
  lat: number;
  lng: number;
  brightness: number;
  frp: number;
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

export interface MonitorState {
  // Core state
  mode: MonitorMode;
  viewState: ViewState;
  selectedEventId: string | null;

  // AI Core
  aiCoreExpanded: boolean;
  aiMessages: { role: 'user' | 'ai'; content: string }[];

  // Panel visibility
  leftPanelOpen: boolean;
  rightPanelOpen: boolean;
  intelPanelOpen: boolean;
  newsPanelOpen: boolean;

  // ── Real-time data ──────────────────────────────────────────────────────
  /** World mode: earthquakes + military flights (backward compat) */
  realEvents: RealEvent[];
  /** GDELT geolocated conflict events (world mode) */
  realWorldEvents: RealEvent[];
  /** GDELT cyber / tech mode events */
  realCyberEvents: RealEvent[];
  /** GDELT finance mode events */
  realFinanceEvents: RealEvent[];
  /** NASA EONET all open natural events (climate layer) */
  realClimateEvents: RealEvent[];
  /** NASA EONET wildfire detections (fire layer) */
  realFireEvents: RealFireEvent[];
  /** CoinGecko crypto + Frankfurter forex tickers */
  realMarketTickers: RealTicker[];
  /** GDELT intelligence articles by current topic */
  gdeltArticles: GdeltArticle[];
  /** GDELT live news for current mode */
  newsArticles: GdeltArticle[];
  /** Currently selected intel topic */
  intelTopic: string;
  /** Data loading indicator */
  dataLoading: boolean;
  /** Timestamp of most recent successful fetch */
  lastFetch: number;

  // ── Actions ─────────────────────────────────────────────────────────────
  setMode: (mode: MonitorMode) => void;
  flyTo: (lng: number, lat: number, zoom?: number) => void;
  selectEvent: (id: string | null) => void;
  toggleAICore: () => void;
  addAIMessage: (role: 'user' | 'ai', content: string) => void;
  toggleLeftPanel: () => void;
  toggleRightPanel: () => void;
  toggleIntelPanel: () => void;
  toggleNewsPanel: () => void;
  setViewState: (vs: ViewState) => void;
  setIntelTopic: (topic: string) => void;
  fetchRealTimeData: () => Promise<void>;
  fetchGdeltIntel: (topic: string) => Promise<void>;
  fetchNews: (mode: MonitorMode) => Promise<void>;
}

/** Default camera */
const DEFAULT_VIEW: ViewState = {
  longitude: 20,
  latitude: 25,
  zoom: 2.2,
  pitch: 35,
  bearing: 0,
  transitionDuration: 0,
};

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

export const useMonitorStore = create<MonitorState>((set, get) => ({
  mode: 'world',
  viewState: DEFAULT_VIEW,
  selectedEventId: null,
  aiCoreExpanded: false,
  aiMessages: [],
  leftPanelOpen: true,
  rightPanelOpen: true,
  intelPanelOpen: false,
  newsPanelOpen: false,
  realEvents: [],
  realWorldEvents: [],
  realCyberEvents: [],
  realFinanceEvents: [],
  realClimateEvents: [],
  realFireEvents: [],
  realMarketTickers: [],
  gdeltArticles: [],
  newsArticles: [],
  intelTopic: 'military',
  dataLoading: false,
  lastFetch: 0,

  // ── fetchRealTimeData: fires all data sources in parallel ────────────────
  fetchRealTimeData: async () => {
    set({ dataLoading: true });
    try {
      const [eqData, flightsData, conflictData, cyberData, financeData, marketData, firesData, climateData] =
        await Promise.all([
          safeFetch('/api/seismology/v1/listEarthquakes', POST_JSON({})),
          safeFetch('/api/military/v1/listMilitaryFlights', POST_JSON({})),
          safeFetch('/api/conflict/v1/listConflictEvents', POST_JSON({})),
          safeFetch('/api/intelligence/v1/searchGdeltDocuments', POST_JSON({ topic: 'cyber', maxRecords: 20 })),
          safeFetch('/api/intelligence/v1/searchGdeltDocuments', POST_JSON({ topic: 'sanctions', maxRecords: 20 })),
          safeFetch('/api/market/v1/getTicker', POST_JSON({})),
          safeFetch('/api/wildfire/v1/listFireDetections', POST_JSON({})),
          safeFetch('/api/climate/v1/listClimateAnomalies', POST_JSON({})),
        ]);

      // ── Earthquakes ──
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
      }));

      // ── Military flights ──
      const realFlights: RealEvent[] = (flightsData.flights || [])
        .filter((f: any) => f.location?.latitude && f.location?.longitude)
        .map((f: any) => ({
          id: f.hexCode,
          title: `${f.type || 'Military Aircraft'} ${f.registration}`,
          location: 'Airspace',
          lat: f.location.latitude,
          lng: f.location.longitude,
          severity: 'high' as Severity,
          category: 'conflict',
          timestamp: 'today',
          description: `Alt: ${Number(f.altitudeFeet || 0).toFixed(0)} ft`,
        }));

      // ── GDELT conflict events ──
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
      }));

      // ── GDELT cyber events ──
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
      }));

      // ── GDELT finance events ──
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
      }));

      // ── Real tickers ──
      const realMarketTickers: RealTicker[] = (marketData.tickers || []);

      // ── Wildfires ──
      const realFireEvents: RealFireEvent[] = (firesData.fireDetections || []).map((f: any) => ({
        id: f.id || Math.random().toString(36).slice(2),
        title: f.title || 'Wildfire',
        lat: f.lat || 0,
        lng: f.lon || 0,
        brightness: f.brightness || 400,
        frp: f.frp || 0,
      })).filter((f: RealFireEvent) => f.lat !== 0 && f.lng !== 0);

      // ── Climate anomalies ──
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
        }));

      set({
        realEvents: [...realEarthquakes, ...realFlights],
        realWorldEvents,
        realCyberEvents,
        realFinanceEvents,
        realClimateEvents,
        realFireEvents,
        realMarketTickers,
        dataLoading: false,
        lastFetch: Date.now(),
      });
    } catch (err) {
      console.error('[SPARK] fetchRealTimeData error:', err);
      set({ dataLoading: false });
    }
  },

  // ── fetchGdeltIntel: load intelligence articles for a topic ──────────────
  fetchGdeltIntel: async (topic: string) => {
    set({ intelTopic: topic });
    const data = await safeFetch('/api/intelligence/v1/searchGdeltDocuments', POST_JSON({ topic, maxRecords: 25 }));
    set({ gdeltArticles: data.articles || [] });
  },

  // ── fetchNews: load news articles for current mode ───────────────────────
  fetchNews: async (mode: MonitorMode) => {
    const data = await safeFetch('/api/news/v1/listNewsArticles', POST_JSON({ mode }));
    set({ newsArticles: data.articles || [] });
  },

  // ── Standard actions ─────────────────────────────────────────────────────
  setMode: (mode) => {
    set({ mode, selectedEventId: null });
    get().fetchNews(mode);
  },

  flyTo: (longitude, latitude, zoom = 5) =>
    set({
      viewState: { longitude, latitude, zoom, pitch: 45, bearing: 0, transitionDuration: 2000 },
    }),

  selectEvent: (id) => set({ selectedEventId: id }),
  toggleAICore: () => set((s) => ({ aiCoreExpanded: !s.aiCoreExpanded })),
  addAIMessage: (role, content) =>
    set((s) => ({ aiMessages: [...s.aiMessages, { role, content }] })),
  toggleLeftPanel: () => set((s) => ({ leftPanelOpen: !s.leftPanelOpen })),
  toggleRightPanel: () => set((s) => ({ rightPanelOpen: !s.rightPanelOpen })),
  toggleIntelPanel: () => set((s) => ({ intelPanelOpen: !s.intelPanelOpen })),
  toggleNewsPanel: () => set((s) => ({ newsPanelOpen: !s.newsPanelOpen })),
  setViewState: (vs) => set({ viewState: { ...vs, transitionDuration: 0 } }),
  setIntelTopic: (topic) => {
    get().fetchGdeltIntel(topic);
  },
}));
