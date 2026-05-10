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
import { useEffect, useState } from 'react';
import { useShallow } from 'zustand/react/shallow';
import { useMonitorStore } from '@/store/useMonitorStore';
import { useContextStore } from '@/store/useContextStore';
import { useUrlState } from '@/hooks/useUrlState';
import { useGlobeSocket } from '@/hooks/useGlobeSocket';
import { MapContainer } from '@/components/monitor/MapContainer';
import { TopBar } from '@/components/monitor/TopBar';
import { AICore } from '@/components/monitor/AICore';
import { useCombatStore, COMBAT_BG } from '@/store/useCombatStore';
import { useCombatWS } from '@/hooks/useCombatWS';
import { useHudTheme } from '@/contexts/ThemeContext';
import { useCommandPalette } from '@/components/monitor/CommandPalette';
import { OpSecBanner } from '@/components/combat/OpSecBanner';

// Layout components
import {
  LeftPanel,
  RightPanel,
  type LeftTab,
  type RightTab,
  StatusBar,
  MobileNav,
  FloatingDock,
  Overlays
} from '@/components/monitor/layout';
import type { StreetViewCoords } from '@/components/monitor/StreetViewPanel';

const MODE_COLORS: Record<string, string> = {
  world:   '#00f5ff',
  tech:    '#a78bfa',
  finance: '#fbbf24',
  happy:   '#34d399',
};

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
  const [combatModalOpen, setCombatModalOpen] = useState(false);
  const combatActive      = useCombatStore((s) => s.isActive);
  const combatActivePanel = useCombatStore((s) => s.activePanel);
  const { hudMode } = useHudTheme();
  useCombatWS();

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
    <div className="h-screen w-screen overflow-hidden flex flex-col" style={{ background: combatActive ? COMBAT_BG : '#010812', transition: 'background 0.5s' }}>

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
      <OpSecBanner />

      {/* ══════════════════════════════════════════════════════════════
          MAIN HUD LAYER  (below TopBar, above status bar)
      ══════════════════════════════════════════════════════════════ */}
      <div className="fixed inset-0 pointer-events-none z-40" style={{ top: '49px', bottom: '32px' }}>
        <div className="relative h-full flex items-stretch gap-2 px-2 py-2">

          {/* ── LEFT PANEL ───────────────────────────────────────── */}
          <LeftPanel
            open={leftPanelOpen}
            tab={leftTab}
            onTabChange={setLeftTab}
            accentColor={accentColor}
            onToggle={toggleLeftPanel}
          />

          {/* ── CENTER SPACER ────────────────────────────────────── */}
          <div className="flex-1 flex flex-col justify-end pointer-events-none">
            {/* AI Core floats above bottom dock */}
            <div className="pointer-events-auto pb-1">
              <AICore />
            </div>
          </div>

          {/* ── RIGHT PANEL ──────────────────────────────────────── */}
          <RightPanel
            open={rightPanelOpen}
            tab={rightTab}
            onTabChange={setRightTab}
            accentColor={accentColor}
            modeColors={MODE_COLORS}
            hudMode={hudMode}
          />
        </div>
      </div>

      {/* ══════════════════════════════════════════════════════════════
          FLOATING QUICK-ACTION DOCK  (bottom-right)
      ══════════════════════════════════════════════════════════════ */}
      <FloatingDock
        layerPanelOpen={layerPanelOpen}
        setLayerPanelOpen={setLayerPanelOpen}
        streetViewMode={streetViewMode}
        setStreetViewMode={setStreetViewMode}
        setStreetViewCoords={setStreetViewCoords}
        caseDrawerOpen={caseDrawerOpen}
        toggleCaseDrawer={toggleCaseDrawer}
        cmdOpen={cmdOpen}
        setCmdOpen={setCmdOpen}
        setCombatModalOpen={setCombatModalOpen}
        accentColor={accentColor}
      />

      {/* ══════════════════════════════════════════════════════════════
          MOBILE BOTTOM NAV  (visible < md)
      ══════════════════════════════════════════════════════════════ */}
      <MobileNav
        mobileTab={mobileTab}
        setMobileTab={setMobileTab}
        accentColor={accentColor}
        modeColors={MODE_COLORS}
        hudMode={hudMode}
      />

      {/* ══════════════════════════════════════════════════════════════
          OVERLAYS
      ══════════════════════════════════════════════════════════════ */}
      <Overlays
        layerPanelOpen={layerPanelOpen}
        setLayerPanelOpen={setLayerPanelOpen}
        caseDrawerOpen={caseDrawerOpen}
        cmdOpen={cmdOpen}
        setCmdOpen={setCmdOpen}
        streetViewMode={streetViewMode}
        setStreetViewMode={setStreetViewMode}
        streetViewCoords={streetViewCoords}
        setStreetViewCoords={setStreetViewCoords}
        combatModalOpen={combatModalOpen}
        setCombatModalOpen={setCombatModalOpen}
        combatActivePanel={combatActivePanel}
        accentColor={accentColor}
      />

      {/* ══════════════════════════════════════════════════════════════
          STATUS BAR  (32px, bottom)
      ══════════════════════════════════════════════════════════════ */}
      <StatusBar
        accentColor={accentColor}
        dataLoading={dataLoading}
        wsConnected={wsConnected}
        providerHealthSummary={providerHealthSummary}
        timeWindow={timeWindow}
        leftPanelOpen={leftPanelOpen}
        rightPanelOpen={rightPanelOpen}
        toggleLeftPanel={toggleLeftPanel}
        toggleRightPanel={toggleRightPanel}
        realEventCount={realEventCount}
        lastFetch={lastFetch}
      />
    </div>
  );
};

export default GlobeMonitor;
