import { ChevronLeft, ChevronRight, Wifi, WifiOff } from 'lucide-react';

interface StatusBarProps {
  accentColor: string;
  dataLoading: boolean;
  wsConnected: boolean;
  providerHealthSummary: { ok: number; degraded: number; down: number } | null;
  timeWindow: string;
  leftPanelOpen: boolean;
  rightPanelOpen: boolean;
  toggleLeftPanel: () => void;
  toggleRightPanel: () => void;
  realEventCount: number;
  lastFetch: number;
}

export function StatusBar({
  accentColor,
  dataLoading,
  wsConnected,
  providerHealthSummary,
  timeWindow,
  leftPanelOpen,
  rightPanelOpen,
  toggleLeftPanel,
  toggleRightPanel,
  realEventCount,
  lastFetch
}: StatusBarProps) {
  return (
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
  );
}
