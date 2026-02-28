/**
 * Globe Monitor — S.P.A.R.K Globe Intelligence HUD
 * Full-bleed HUD with floating glassmorphic panels over the CartoDB black globe.
 *
 * Features:
 *   - URL state sync (shareable links)
 *   - Time-window filtering (1h/6h/24h/48h/7d) in TopBar
 *   - Activity tracking (NEW badges, seen detection)
 *   - Signal Fusion panel (causal correlations)
 *   - Custom Monitor panel (keyword-based alerts with colors)
 *   - Snapshot + Playback (IndexedDB timeline)
 *   - Case Drawer (investigation workflow, persistent cases + notes)
 *   - Provider Health panel (circuit-breaker status per data source)
 *   - Zoom-adaptive clustering + layer visibility on map
 *
 * Layout:
 *   Left column  (19rem):  ThreatMatrix + LiveNewsPanel + CustomMonitorPanel
 *   Right column (18rem):  InstabilityIndex + GdeltIntelPanel + FusionPanel + ProviderHealthPanel
 *   Bottom-left  (18rem):  ClimateAnomalyPanel
 *   Bottom-right (16rem):  SnapshotPlayback (floating pill)
 *   Bottom-center:         AICore
 *   Right edge:            CaseDrawer (slide-in)
 *   Screen edges:          4× HUD corner brackets + scan-line overlay + status bar
 */
import { useCallback, useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMonitorStore } from '@/store/useMonitorStore';
import { useUrlState } from '@/hooks/useUrlState';
import { useGlobeSocket } from '@/hooks/useGlobeSocket';
import { MapContainer } from '@/components/monitor/MapContainer';
import { TopBar } from '@/components/monitor/TopBar';
import { ThreatMatrix } from '@/components/monitor/ThreatMatrix';
import { InstabilityIndex } from '@/components/monitor/InstabilityIndex';
import { GdeltIntelPanel } from '@/components/monitor/GdeltIntelPanel';
import { LiveNewsPanel } from '@/components/monitor/LiveNewsPanel';
import { ClimateAnomalyPanel } from '@/components/monitor/ClimateAnomalyPanel';
import { FusionPanel } from '@/components/monitor/FusionPanel';
import { CustomMonitorPanel } from '@/components/monitor/CustomMonitorPanel';
import { SnapshotPlayback } from '@/components/monitor/SnapshotPlayback';
import { CaseDrawer } from '@/components/monitor/CaseDrawer';
import ProviderHealthPanel from '@/components/monitor/ProviderHealthPanel';
import { LayerTogglePanel } from '@/components/monitor/LayerTogglePanel';
import { AICore } from '@/components/monitor/AICore';

/* Per-mode accent colors (shared with TopBar) */
const MODE_COLORS: Record<string, string> = {
  world:   '#00f5ff',
  tech:    '#a78bfa',
  finance: '#fbbf24',
  happy:   '#34d399',
};

const WorldMonitor = () => {
  const leftPanelOpen  = useMonitorStore((s) => s.leftPanelOpen);
  const rightPanelOpen = useMonitorStore((s) => s.rightPanelOpen);
  const mode           = useMonitorStore((s) => s.mode);
  const fetchRealTimeData = useMonitorStore((s) => s.fetchRealTimeData);
  const dataLoading    = useMonitorStore((s) => s.dataLoading);
  const lastFetch      = useMonitorStore((s) => s.lastFetch);

  const accentColor = MODE_COLORS[mode] ?? '#00f5ff';
  // ── WebSocket real-time push (Globe /ws/globe) ──────────────────
  useGlobeSocket();

  // ── Layer toggle panel state ───────────────────────────────
  const [layerPanelOpen, setLayerPanelOpen] = useState(false);
  const wsConnected = useMonitorStore((s) => s.wsConnected);
  // ── URL state sync ───────────────────────────────────────────────────────
  // Reads initial URL hash into store + keeps URL in sync with store changes
  useUrlState();

  // ── Poll real-time data every 30 s ───────────────────────────────────────
  useEffect(() => {
    fetchRealTimeData();
    const interval = setInterval(fetchRealTimeData, 30_000);
    return () => clearInterval(interval);
  }, [fetchRealTimeData]);

  // ── Subtle parallax on mouse move ────────────────────────────────────────
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const rafRef = useRef<number>(0);
  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(() => {
      setMousePos({
        x: (e.clientX / window.innerWidth - 0.5) * 2,
        y: (e.clientY / window.innerHeight - 0.5) * 2,
      });
    });
  }, []);

  return (
    <div
      className="h-screen w-screen overflow-hidden"
      style={{ background: '#010812' }}
      onMouseMove={handleMouseMove}
    >
      {/* ── Base layer: CartoDB black globe ─────────────────────── */}
      <MapContainer />

      {/* ── Scan-line overlay ────────────────────────────────────── */}
      <div className="scan-overlay" />

      {/* ── Atmosphere gradient ──────────────────────────────────── */}
      <div className="absolute inset-0 atmosphere-glow pointer-events-none" />

      {/* ── Screen-level HUD corner brackets ─────────────────────── */}
      <span
        className="hud-screen-corner hud-corner-tl"
        style={{ borderColor: accentColor, opacity: 0.5 }}
      />
      <span
        className="hud-screen-corner hud-corner-tr"
        style={{ borderColor: accentColor, opacity: 0.5 }}
      />
      <span
        className="hud-screen-corner hud-corner-bl"
        style={{ borderColor: accentColor, opacity: 0.35 }}
      />
      <span
        className="hud-screen-corner hud-corner-br"
        style={{ borderColor: accentColor, opacity: 0.35 }}
      />

      {/* ── Top Bar (with TimeFilterBar + share button) ───────────── */}
      <TopBar />

      {/* ── Floating HUD panels with subtle parallax ─────────────── */}
      <div className="fixed inset-0 pointer-events-none pt-14 pb-5 px-3 z-40">
        <div
          className="relative h-full flex gap-3"
          style={{
            transform: `translate(${mousePos.x * 3}px, ${mousePos.y * 2}px)`,
            transition: 'transform 0.12s ease-out',
          }}
        >
          {/* ── LEFT COLUMN ─────────────────────────────────────── */}
          <AnimatePresence mode="wait">
            {leftPanelOpen && (
              <motion.div
                key={`left-${mode}`}
                initial={{ opacity: 0, x: -32, scale: 0.97 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: -24, scale: 0.97 }}
                transition={{ type: 'spring', stiffness: 260, damping: 26 }}
                className="pointer-events-auto w-76 hidden md:flex flex-col gap-2 overflow-y-auto scrollbar-hud pb-2"
                style={{ maxHeight: 'calc(100vh - 9rem)', width: '19rem' }}
              >
                <ThreatMatrix accentColor={accentColor} />
                <LiveNewsPanel accentColor={accentColor} />
                <CustomMonitorPanel accentColor={accentColor} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── CENTER SPACER ────────────────────────────────────── */}
          <div className="flex-1" />

          {/* ── RIGHT COLUMN ─────────────────────────────────────── */}
          <AnimatePresence mode="wait">
            {rightPanelOpen && (
              <motion.div
                key="right-panel"
                initial={{ opacity: 0, x: 32, scale: 0.97 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 24, scale: 0.97 }}
                transition={{ type: 'spring', stiffness: 260, damping: 26 }}
                className="pointer-events-auto hidden md:flex flex-col gap-2 overflow-y-auto scrollbar-hud pb-2"
                style={{ maxHeight: 'calc(100vh - 9rem)', width: '18rem' }}
              >
                <InstabilityIndex accentColor={accentColor} />
                <GdeltIntelPanel accentColor={accentColor} />
                <FusionPanel accentColor={MODE_COLORS.tech} />
                <ProviderHealthPanel accentColor={accentColor} />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ── BOTTOM-LEFT: Climate Anomalies ────────────────────────── */}
      <AnimatePresence>
        <motion.div
          key="climate-panel"
          initial={{ opacity: 0, y: 24, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 16, scale: 0.96 }}
          transition={{ type: 'spring', stiffness: 240, damping: 26, delay: 0.25 }}
          className="fixed bottom-6 left-3 pointer-events-auto z-40 hidden md:block"
          style={{ width: '18rem' }}
        >
          <ClimateAnomalyPanel accentColor={accentColor} />
        </motion.div>
      </AnimatePresence>

      {/* ── BOTTOM-CENTER: AI Core ────────────────────────────────── */}
      <AICore />

      {/* ── BOTTOM-RIGHT: Snapshot Playback ──────────────────────── */}
      <SnapshotPlayback accentColor={accentColor} />

      {/* ── RIGHT EDGE: Case Drawer (investigation mode) ──────────── */}
      <CaseDrawer accentColor={accentColor} />

      {/* ── LAYER TOGGLE BUTTON (top-right floating) ─────────────── */}
      <button
        onClick={() => setLayerPanelOpen((v) => !v)}
        className="fixed top-16 right-4 z-40 pointer-events-auto
                   flex items-center gap-1.5 rounded-lg px-3 py-2
                   border border-white/20 bg-gray-900/80 backdrop-blur-sm
                   text-xs font-semibold text-white hover:bg-white/10
                   transition-colors duration-150"
        title="Toggle layer visibility"
      >
        <span>⊞</span>
        <span>Layers</span>
      </button>

      {/* ── LAYER TOGGLE PANEL ────────────────────────────────────── */}
      <LayerTogglePanel open={layerPanelOpen} onClose={() => setLayerPanelOpen(false)} />

      {/* ── STATUS BAR ───────────────────────────────────────────── */}
      <div className="hud-status-bar">
        <span
          className="status-dot shrink-0"
          style={{ background: dataLoading ? '#fbbf24' : accentColor }}
        />
        <span style={{ color: dataLoading ? '#fbbf24' : accentColor, opacity: 0.7 }}>
          {dataLoading ? 'SYNCING DATA…' : 'ALL FEEDS NOMINAL'}
        </span>
        {/* WebSocket push indicator */}
        <span
          className="ml-2 flex items-center gap-1 text-[10px] opacity-70"
          title={wsConnected ? 'Globe WS push active' : 'Globe WS disconnected'}
        >
          <span
            className="inline-block w-1.5 h-1.5 rounded-full"
            style={{ background: wsConnected ? '#34d399' : '#6b7280' }}
          />
          {wsConnected ? 'WS' : 'REST'}
        </span>
        <span className="ml-auto opacity-50">© CARTO · © OpenStreetMap contributors</span>
        {lastFetch > 0 && (
          <span className="opacity-40">
            LAST SYNC {new Date(lastFetch).toISOString().slice(11, 19)} UTC
          </span>
        )}
      </div>
    </div>
  );
};

export default WorldMonitor;
