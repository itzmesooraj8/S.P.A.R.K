/**
 * SPARK Globe Monitor — S.P.A.R.K Globe Intelligence HUD
 *
 * Layout:
 *   Top:          TopBar (48px) — brand, modes, live status, map controls, clock
 *   Left drawer:  3 tabs — THREATS | INTEL | MONITOR  (collapsible, 19rem)
 *   Right drawer: 3 tabs — SIGNAL | HEALTH | ARCHIVE  (collapsible, 18rem)
 *   Bottom dock:  status bar + quick-action icon cluster
 *   Overlays:     AICore (floating center), CaseDrawer (slide-in right edge)
 *   Mobile:       bottom tab nav instead of side drawers
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle, Newspaper, Settings2,
  BarChart3, HeartPulse, Archive,
  Layers2, BookOpen, Keyboard, Wifi, WifiOff,
  ChevronLeft, ChevronRight, Eye,
} from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { useContextStore } from '@/store/useContextStore';
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
import { CommandPalette, useCommandPalette } from '@/components/monitor/CommandPalette';
import { StreetViewPanel, type StreetViewCoords } from '@/components/monitor/StreetViewPanel';

const MODE_COLORS: Record<string, string> = {
  world:   '#00f5ff',
  tech:    '#a78bfa',
  finance: '#fbbf24',
  happy:   '#34d399',
};

/* ── Tab definitions ─────────────────────────────────────────────────────── */
const LEFT_TABS = [
  { id: 'threats', label: 'THREATS', icon: AlertTriangle },
  { id: 'intel',   label: 'INTEL',   icon: Newspaper },
  { id: 'monitor', label: 'MONITOR', icon: Settings2 },
] as const;

const RIGHT_TABS = [
  { id: 'signal',  label: 'SIGNAL',  icon: BarChart3 },
  { id: 'health',  label: 'HEALTH',  icon: HeartPulse },
  { id: 'archive', label: 'ARCHIVE', icon: Archive },
] as const;

type LeftTab  = typeof LEFT_TABS[number]['id'];
type RightTab = typeof RIGHT_TABS[number]['id'];

/* ── Reusable glassy panel tab-bar ───────────────────────────────────────── */
function PanelTabs<T extends string>({
  tabs, active, onSelect, accentColor,
}: {
  tabs: readonly { id: T; label: string; icon: React.ComponentType<{ size?: number }> }[];
  active: T;
  onSelect: (id: T) => void;
  accentColor: string;
}) {
  return (
    <div
      className="flex items-center gap-px shrink-0"
      style={{
        background: 'rgba(255,255,255,0.025)',
        borderBottom: `1px solid rgba(255,255,255,0.06)`,
      }}
    >
      {tabs.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onSelect(id)}
          className="relative flex-1 flex items-center justify-center gap-1.5 py-2 text-[9px] font-bold
                     tracking-[0.18em] font-mono transition-colors duration-200"
          style={{ color: active === id ? accentColor : 'rgba(255,255,255,0.3)' }}
        >
          {active === id && (
            <motion.div
              layoutId={`tab-bg-${tabs[0].id}`}
              className="absolute inset-0"
              style={{ background: `${accentColor}10`, borderBottom: `2px solid ${accentColor}` }}
              transition={{ type: 'spring', stiffness: 400, damping: 32 }}
            />
          )}
          <Icon size={10} className="relative z-10 shrink-0" />
          <span className="relative z-10">{label}</span>
        </button>
      ))}
    </div>
  );
}

/* ── Panel wrapper shared styles ─────────────────────────────────────────── */
function PanelShell({
  children, accentColor, width = '19rem',
}: {
  children: React.ReactNode;
  accentColor: string;
  width?: string;
}) {
  return (
    <div
      className="h-full flex flex-col rounded-xl overflow-hidden"
      style={{
        width,
        background: 'rgba(2, 8, 20, 0.82)',
        border: `1px solid ${accentColor}18`,
        backdropFilter: 'blur(28px) saturate(1.3)',
        boxShadow: `0 0 40px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04)`,
      }}
    >
      {children}
    </div>
  );
}

const GlobeMonitor = () => {
  const leftPanelOpen     = useMonitorStore((s) => s.leftPanelOpen);
  const rightPanelOpen    = useMonitorStore((s) => s.rightPanelOpen);
  const toggleLeftPanel   = useMonitorStore((s) => s.toggleLeftPanel);
  const toggleRightPanel  = useMonitorStore((s) => s.toggleRightPanel);
  const toggleCaseDrawer  = useMonitorStore((s) => s.toggleCaseDrawer);
  const caseDrawerOpen    = useMonitorStore((s) => s.caseDrawerOpen);
  const mode              = useMonitorStore((s) => s.mode);
  const fetchRealTimeData = useMonitorStore((s) => s.fetchRealTimeData);
  const dataLoading       = useMonitorStore((s) => s.dataLoading);
  const lastFetch         = useMonitorStore((s) => s.lastFetch);
  const wsConnected       = useMonitorStore((s) => s.wsConnected);
  const timeWindow        = useMonitorStore((s) => s.timeWindow);
  const providerHealthSummary = useMonitorStore((s) => s.providerHealthSummary);
  const realEventCount    = useMonitorStore((s) =>
    s.realEvents.length + s.realWorldEvents.length + s.realCyberEvents.length +
    s.realFireEvents.length + s.realClimateEvents.length);
  const selectedEventId   = useMonitorStore((s) => s.selectedEventId);
  const allRealEvents     = useMonitorStore(
    useShallow((s) => [
      ...s.realEvents, ...s.realWorldEvents, ...s.realCyberEvents, ...s.realClimateEvents,
    ])
  );

  const { setSelectedItem } = useContextStore();

  const accentColor = MODE_COLORS[mode] ?? '#00f5ff';
  const { open: cmdOpen, setOpen: setCmdOpen } = useCommandPalette();

  const [leftTab,        setLeftTab]        = useState<LeftTab>('threats');
  const [rightTab,       setRightTab]       = useState<RightTab>('signal');
  const [layerPanelOpen, setLayerPanelOpen] = useState(false);
  const [streetViewCoords, setStreetViewCoords] = useState<StreetViewCoords | null>(null);
  const [streetViewMode, setStreetViewMode] = useState(false);
  // Mobile: which bottom-tab is open (null = map only)
  const [mobileTab, setMobileTab] = useState<'left' | 'right' | null>(null);

  useGlobeSocket();
  useUrlState();

  useEffect(() => {
    fetchRealTimeData();
    const id = setInterval(fetchRealTimeData, 30_000);
    return () => clearInterval(id);
  }, [fetchRealTimeData]);

  // Sync selected globe event → global context store (enables pronoun resolution in Command Bar)
  useEffect(() => {
    if (!selectedEventId) return;
    const event = allRealEvents.find((e) => e.id === selectedEventId);
    if (event) {
      setSelectedItem({
        module: 'globe',
        type: event.category ?? 'event',
        label: event.title,
        data: { id: event.id, location: event.location, severity: event.severity, description: event.description, lat: event.lat, lng: event.lng },
      });
    }
  }, [selectedEventId, setSelectedItem]); // allRealEvents intentionally omitted to avoid thrash

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col" style={{ background: '#010812' }}>

      {/* ── Globe base ───────────────────────────────────────────── */}
      <MapContainer
        onMapClick={streetViewMode ? (loc) => setStreetViewCoords({ ...loc }) : undefined}
      />

      {/* ── Atmospheric overlays ─────────────────────────────────── */}
      <div className="scan-overlay" />
      <div className="absolute inset-0 atmosphere-glow pointer-events-none" />

      {/* ── HUD corner brackets ──────────────────────────────────── */}
      {(['tl','tr','bl','br'] as const).map((pos) => (
        <span
          key={pos}
          className={`hud-screen-corner hud-corner-${pos}`}
          style={{ borderColor: accentColor, opacity: pos.startsWith('t') ? 0.5 : 0.3 }}
        />
      ))}

      {/* ══════════════════════════════════════════════════════════════
          TOP BAR
      ══════════════════════════════════════════════════════════════ */}
      <TopBar />

      {/* ══════════════════════════════════════════════════════════════
          MAIN HUD LAYER  (below TopBar, above status bar)
      ══════════════════════════════════════════════════════════════ */}
      <div className="fixed inset-0 pointer-events-none z-40" style={{ top: '49px', bottom: '32px' }}>
        <div className="relative h-full flex items-stretch gap-2 px-2 py-2">

          {/* ── LEFT PANEL ───────────────────────────────────────── */}
          <AnimatePresence>
            {leftPanelOpen && (
              <motion.div
                key="left-panel"
                initial={{ opacity: 0, x: -48, scale: 0.96 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: -40, scale: 0.96 }}
                transition={{ type: 'spring', stiffness: 300, damping: 28 }}
                className="pointer-events-auto hidden md:flex flex-col shrink-0 group"
                style={{ width: '19rem', height: '100%' }}
              >
                <PanelShell accentColor={accentColor} width="19rem">
                  {/* Tab bar */}
                  <PanelTabs tabs={LEFT_TABS} active={leftTab} onSelect={setLeftTab} accentColor={accentColor} />

                  {/* Tab content */}
                  <div className="flex-1 overflow-y-auto scrollbar-hud">
                    <AnimatePresence mode="wait">
                      {leftTab === 'threats' && (
                        <motion.div key="threats" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                          <ThreatMatrix accentColor={accentColor} />
                        </motion.div>
                      )}
                      {leftTab === 'intel' && (
                        <motion.div key="intel" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                          <LiveNewsPanel accentColor={accentColor} />
                          <GdeltIntelPanel accentColor={accentColor} />
                        </motion.div>
                      )}
                      {leftTab === 'monitor' && (
                        <motion.div key="monitor" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                          <CustomMonitorPanel accentColor={accentColor} />
                          <ClimateAnomalyPanel accentColor={accentColor} />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </PanelShell>

                {/* Collapse handle */}
                <button
                  onClick={toggleLeftPanel}
                  className="absolute -right-3 top-1/2 -translate-y-1/2 w-5 h-10 rounded-r-md flex items-center justify-center
                             opacity-0 group-hover:opacity-100 transition-opacity pointer-events-auto"
                  style={{ background: `${accentColor}20`, border: `1px solid ${accentColor}30`, color: accentColor }}
                >
                  <ChevronLeft size={12} />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* ── CENTER SPACER ────────────────────────────────────── */}
          <div className="flex-1 flex flex-col justify-end pointer-events-none">
            {/* AI Core floats above bottom dock */}
            <div className="pointer-events-auto pb-1">
              <AICore />
            </div>
          </div>

          {/* ── RIGHT PANEL ──────────────────────────────────────── */}
          <AnimatePresence>
            {rightPanelOpen && (
              <motion.div
                key="right-panel"
                initial={{ opacity: 0, x: 48, scale: 0.96 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 40, scale: 0.96 }}
                transition={{ type: 'spring', stiffness: 300, damping: 28 }}
                className="pointer-events-auto hidden md:flex flex-col shrink-0"
                style={{ width: '18rem', height: '100%' }}
              >
                <PanelShell accentColor={accentColor} width="18rem">
                  <PanelTabs tabs={RIGHT_TABS} active={rightTab} onSelect={setRightTab} accentColor={accentColor} />

                  <div className="flex-1 overflow-y-auto scrollbar-hud">
                    <AnimatePresence mode="wait">
                      {rightTab === 'signal' && (
                        <motion.div key="signal" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                          <InstabilityIndex accentColor={accentColor} />
                          <FusionPanel accentColor={MODE_COLORS.tech} />
                        </motion.div>
                      )}
                      {rightTab === 'health' && (
                        <motion.div key="health" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                          <ProviderHealthPanel accentColor={accentColor} />
                        </motion.div>
                      )}
                      {rightTab === 'archive' && (
                        <motion.div key="archive" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                          <SnapshotPlayback accentColor={accentColor} mode="inline" />
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                </PanelShell>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          FLOATING QUICK-ACTION DOCK  (bottom-right)
      ══════════════════════════════════════════════════════════════ */}
      <div
        className="fixed bottom-9 right-3 z-50 pointer-events-auto flex-col gap-1.5 items-end hidden md:flex"
      >
        {/* Layers */}
        <DockButton
          icon={<Layers2 size={14} />}
          label="Layers"
          active={layerPanelOpen}
          accentColor={accentColor}
          onClick={() => setLayerPanelOpen((v) => !v)}
        />
        {/* Street View */}
        <DockButton
          icon={<Eye size={14} />}
          label="Street View"
          active={streetViewMode}
          accentColor={accentColor}
          onClick={() => {
            setStreetViewMode((v) => !v);
            if (streetViewMode) setStreetViewCoords(null);
          }}
        />
        {/* Cases */}
        <DockButton
          icon={<BookOpen size={14} />}
          label="Cases"
          active={caseDrawerOpen}
          accentColor={accentColor}
          onClick={toggleCaseDrawer}
        />
        {/* Command palette hint */}
        <DockButton
          icon={<Keyboard size={14} />}
          label="⌃K"
          active={cmdOpen}
          accentColor={accentColor}
          onClick={() => setCmdOpen(true)}
        />
      </div>

      {/* ══════════════════════════════════════════════════════════════
          MOBILE BOTTOM NAV  (visible < md)
      ══════════════════════════════════════════════════════════════ */}
      <div
        className="fixed bottom-0 left-0 right-0 z-50 flex md:hidden items-center"
        style={{
          background: 'rgba(1,8,20,0.97)',
          borderTop: `1px solid ${accentColor}20`,
          backdropFilter: 'blur(20px)',
          height: '52px',
        }}
      >
        {[
          { id: 'left' as const,  label: 'THREATS', icon: AlertTriangle },
          { id: null,             label: 'MAP',      icon: null },
          { id: 'right' as const, label: 'SIGNAL',   icon: BarChart3 },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={label}
            onClick={() => setMobileTab(mobileTab === id ? null : id)}
            className="flex-1 flex flex-col items-center justify-center gap-1 text-[9px] font-mono
                       font-bold tracking-widest transition-colors duration-200"
            style={{ color: mobileTab === id ? accentColor : 'rgba(255,255,255,0.3)' }}
          >
            {Icon ? <Icon size={16} /> : (
              <div className="w-4 h-4 rounded-full border" style={{ borderColor: mobileTab === id ? accentColor : 'rgba(255,255,255,0.2)', background: mobileTab === id ? `${accentColor}20` : 'transparent' }} />
            )}
            {label}
          </button>
        ))}
      </div>

      {/* Mobile panel overlay */}
      <AnimatePresence>
        {mobileTab && (
          <motion.div
            key={`mobile-${mobileTab}`}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className="fixed bottom-[52px] left-0 right-0 z-40 md:hidden rounded-t-2xl overflow-hidden"
            style={{
              height: '60vh',
              background: 'rgba(2,8,20,0.97)',
              border: `1px solid ${accentColor}20`,
              backdropFilter: 'blur(28px)',
            }}
          >
            <div className="h-full overflow-y-auto scrollbar-hud p-3 flex flex-col gap-2">
              {mobileTab === 'left' && (
                <>
                  <ThreatMatrix accentColor={accentColor} />
                  <LiveNewsPanel accentColor={accentColor} />
                  <GdeltIntelPanel accentColor={accentColor} />
                  <CustomMonitorPanel accentColor={accentColor} />
                </>
              )}
              {mobileTab === 'right' && (
                <>
                  <InstabilityIndex accentColor={accentColor} />
                  <FusionPanel accentColor={MODE_COLORS.tech} />
                  <ProviderHealthPanel accentColor={accentColor} />
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ══════════════════════════════════════════════════════════════
          OVERLAYS
      ══════════════════════════════════════════════════════════════ */}
      <LayerTogglePanel open={layerPanelOpen} onClose={() => setLayerPanelOpen(false)} />
      <CaseDrawer accentColor={accentColor} />
      <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} accentColor={accentColor} />
      {/* Street View panel — shown when streetViewMode is active and coords picked */}
      {streetViewMode && (
        <StreetViewPanel
          coords={streetViewCoords}
          onClose={() => { setStreetViewMode(false); setStreetViewCoords(null); }}
          accentColor={accentColor}
        />
      )}
      {streetViewMode && !streetViewCoords && (
        <div
          className="fixed bottom-10 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-full text-[10px] font-mono font-bold tracking-widest pointer-events-none"
          style={{ background: `${accentColor}20`, border: `1px solid ${accentColor}50`, color: accentColor }}
        >
          STREET VIEW ACTIVE — CLICK ANY LOCATION ON THE GLOBE
        </div>
      )}

      {/* ══════════════════════════════════════════════════════════════
          STATUS BAR  (32px, bottom)
      ══════════════════════════════════════════════════════════════ */}
      <div
        className="hud-status-bar hidden md:flex"
        style={{
          borderTop: `1px solid ${accentColor}14`,
          background: 'rgba(1,6,18,0.92)',
          backdropFilter: 'blur(16px)',
        }}
      >
        {/* Left: feed status + provider health summary */}
        <div className="flex items-center gap-3">
          <span
            className="status-dot shrink-0"
            style={{ background: dataLoading ? '#fbbf24' : accentColor, boxShadow: `0 0 6px ${dataLoading ? '#fbbf2460' : `${accentColor}60`}` }}
          />
          <span className="text-[9px] font-mono font-bold tracking-widest" style={{ color: dataLoading ? '#fbbf24' : accentColor }}>
            {dataLoading ? 'SYNCING…' : 'FEEDS NOMINAL'}
          </span>
          <span className="flex items-center gap-1 text-[9px] font-mono" title={wsConnected ? 'Globe WebSocket active' : 'WebSocket offline'}>
            {wsConnected
              ? <Wifi size={9} style={{ color: '#34d399' }} />
              : <WifiOff size={9} style={{ color: '#6b7280' }} />}
            <span style={{ color: wsConnected ? '#34d399' : '#6b7280', opacity: 0.7 }}>{wsConnected ? 'WS' : 'OFF'}</span>
          </span>

          {/* Provider health mini-summary */}
          {providerHealthSummary && (
            <div className="hidden xl:flex items-center gap-2 pl-1 border-l border-white/8">
              <span className="text-[8px] font-mono" style={{ color: '#34d399', opacity: 0.7 }}>
                {providerHealthSummary.ok}✓
              </span>
              {providerHealthSummary.degraded > 0 && (
                <span className="text-[8px] font-mono" style={{ color: '#fbbf24' }}>
                  {providerHealthSummary.degraded}⚠
                </span>
              )}
              {providerHealthSummary.down > 0 && (
                <span className="text-[8px] font-mono" style={{ color: '#f87171' }}>
                  {providerHealthSummary.down}✗
                </span>
              )}
            </div>
          )}

          {/* Time window indicator */}
          <div className="hidden lg:flex items-center gap-1 pl-1 border-l border-white/8">
            <span className="text-[8px] font-mono tracking-wider opacity-40">WINDOW</span>
            <span className="text-[8px] font-mono font-bold tracking-wider" style={{ color: accentColor, opacity: 0.8 }}>
              {timeWindow.toUpperCase()}
            </span>
          </div>
        </div>

        {/* Center: event count + panel toggle shortcuts */}
        <div className="flex items-center gap-3 mx-auto">
          <button
            onClick={toggleLeftPanel}
            className="flex items-center gap-1 text-[9px] font-mono tracking-widest transition-colors duration-150 hover:opacity-100 opacity-40"
            style={{ color: leftPanelOpen ? accentColor : 'rgba(255,255,255,0.5)' }}
          >
            <ChevronLeft size={9} />
            {leftPanelOpen ? 'HIDE LEFT' : 'SHOW LEFT'}
          </button>
          <div className="w-px h-3 bg-white/10" />
          {/* Live event count badge */}
          <div
            className="flex items-center gap-1 px-2 py-0.5 rounded font-mono text-[8px] font-bold tracking-wider"
            style={{
              background: `${accentColor}10`,
              border: `1px solid ${accentColor}25`,
              color: accentColor,
              opacity: 0.8,
            }}
          >
            <span
              className="w-1.5 h-1.5 rounded-full shrink-0"
              style={{ background: accentColor, boxShadow: `0 0 4px ${accentColor}` }}
            />
            {realEventCount > 0 ? `${realEventCount} ACTIVE` : 'NO DATA'}
          </div>
          <div className="w-px h-3 bg-white/10" />
          <button
            onClick={toggleRightPanel}
            className="flex items-center gap-1 text-[9px] font-mono tracking-widest transition-colors duration-150 hover:opacity-100 opacity-40"
            style={{ color: rightPanelOpen ? accentColor : 'rgba(255,255,255,0.5)' }}
          >
            {rightPanelOpen ? 'HIDE RIGHT' : 'SHOW RIGHT'}
            <ChevronRight size={9} />
          </button>
        </div>

        {/* Right: credits + sync time */}
        <div className="flex items-center gap-3 ml-auto">
          <span className="hidden xl:inline text-[8px] font-mono opacity-25 tracking-wider">
            © CARTO · © OpenStreetMap
          </span>
          {lastFetch > 0 && (
            <span className="text-[8px] font-mono opacity-35 tracking-wider">
              SYNC {new Date(lastFetch).toISOString().slice(11, 19)} UTC
            </span>
          )}
        </div>
      </div>
    </div>
  );
};

/* ── Dock icon button ─────────────────────────────────────────────────────── */
function DockButton({
  icon, label, active, accentColor, onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  accentColor: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 pl-2.5 pr-3 py-1.5 rounded-lg text-[10px] font-mono
                 font-bold tracking-widest transition-all duration-200 group"
      style={{
        background: active ? `${accentColor}18` : 'rgba(2,8,20,0.82)',
        border: `1px solid ${active ? `${accentColor}45` : 'rgba(255,255,255,0.09)'}`,
        color: active ? accentColor : 'rgba(255,255,255,0.45)',
        backdropFilter: 'blur(16px)',
        boxShadow: active ? `0 0 14px ${accentColor}22` : '0 2px 12px rgba(0,0,0,0.3)',
      }}
      title={label}
    >
      <span style={{ color: active ? accentColor : 'rgba(255,255,255,0.4)' }}>{icon}</span>
      <span>{label}</span>
    </button>
  );
}

export default GlobeMonitor;

