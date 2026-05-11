import { useState, useEffect, useRef, useCallback } from 'react';
import { useHudTheme } from '@/contexts/ThemeContext';
import { Zap, LogOut, User, WifiOff, Volume2, VolumeX, Bell, Settings } from 'lucide-react';
import { useAuth } from '@/contexts/AuthContext';
import { useConnectionStore } from '@/store/useConnectionStore';
import { useAlertStore } from '@/store/useAlertStore';
import type { WsStatus } from '@/store/useConnectionStore';
import HudModeChip from './HudModeChip';

type SystemMode = 'PASSIVE' | 'ACTIVE' | 'COMBAT';

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

function FlipDigits({ value }: { value: string }) {
  return (
    <span className="inline-flex gap-0.5">
      {value.split('').map((d, i) => (
        <span
          key={i}
          className="font-orbitron text-hud-cyan inline-block w-[0.85em] text-center"
          style={{ textShadow: '0 0 8px hsl(186 100% 50% / 0.8), 0 0 20px hsl(186 100% 50% / 0.4)' }}
        >
          {d}
        </span>
      ))}
    </span>
  );
}

function TopBarClock() {
  const [now, setNow] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const hh = now.getHours();
  const ampm = hh >= 12 ? 'PM' : 'AM';
  const hh12 = hh % 12 || 12;
  const hhStr = hh12.toString().padStart(2, '0');
  const mm = now.getMinutes().toString().padStart(2, '0');
  const ss = now.getSeconds().toString().padStart(2, '0');
  const dateStr = `${now.getDate().toString().padStart(2, '0')}.${MONTHS[now.getMonth()]}.${now.getFullYear()}`;

  return (
    <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 flex flex-col items-center pointer-events-none">
      <div className="flex items-center gap-1 font-orbitron text-xl font-bold">
        <FlipDigits value={hhStr} />
        <span className="neon-text animate-blink">:</span>
        <FlipDigits value={mm} />
        <span className="neon-text animate-blink">:</span>
        <FlipDigits value={ss} />
        <span className="ml-2 text-xs text-hud-cyan/70">{ampm}</span>
      </div>
      <div className="font-rajdhani text-[10px] text-hud-cyan/60 tracking-widest mt-0.5">{dateStr}</div>
    </div>
  );
}

function ConnectionBadge() {
  const coreOnline  = useConnectionStore((s) => s.coreOnline);
  const aiOnline    = useConnectionStore((s) => s.aiOnline);
  const coreStatus  = useConnectionStore((s) => s.coreStatus);
  const aiStatus    = useConnectionStore((s) => s.aiStatus);
  const coreLast    = useConnectionStore((s) => s.coreLastConnected);
  const aiLast      = useConnectionStore((s) => s.aiLastConnected);
  const coreCode    = useConnectionStore((s) => s.coreLastCloseCode);
  const aiCode      = useConnectionStore((s) => s.aiLastCloseCode);
  const bumpRetry   = useConnectionStore((s) => s.bumpRetry);

  const bothOnline       = coreOnline && aiOnline;
  const backendOnline    = coreOnline || aiOnline;
  const partial          = coreOnline !== aiOnline;
  const bothIdle         = coreStatus === 'idle' && aiStatus === 'idle';
  const anyReconnecting  = coreStatus === 'reconnecting' || aiStatus === 'reconnecting';

  const badgeLabel = bothOnline     ? 'ONLINE'
    : bothIdle       ? 'STANDBY'
    : !backendOnline && anyReconnecting ? 'RECONNECTING'
    : !backendOnline ? 'OFFLINE'
    : !aiOnline      ? 'AI DEGRADED'
    :                  'CORE DEGRADED';

  const badgeColor = bothOnline     ? '#30d158'
    : bothIdle       ? '#636366'
    : partial        ? '#ff9f0a'
    : anyReconnecting ? '#ff9f0a'
    :                   '#ff453a';

  const badgePulse = !bothOnline && !bothIdle;

  const [showConnFlyout, setShowConnFlyout] = useState(false);
  const flyoutRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showConnFlyout) return;
    const handler = (e: MouseEvent) => {
      if (flyoutRef.current && !flyoutRef.current.contains(e.target as Node)) {
        setShowConnFlyout(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, [showConnFlyout]);

  const fmtTime = useCallback((ms: number | null) => {
    if (!ms) return '—';
    return new Date(ms).toTimeString().slice(0, 8);
  }, []);

  const statusColor = (s: WsStatus) =>
    s === 'connected'    ? '#30d158'
    : s === 'reconnecting' ? '#ff9f0a'
    : s === 'idle'         ? '#636366'
    :                        '#ff453a';

  const closeCodeLabel = useCallback((code: number | null): string | null => {
    if (code === null) return null;
    const labels: Record<number, string> = {
      1000: 'Normal',
      1001: 'Going Away',
      1006: 'Abnormal',
      1011: 'Server Error',
      1012: 'Service Restart',
      1013: 'Try Again Later',
    };
    return `${code}${labels[code] ? ` · ${labels[code]}` : ''}`;
  }, []);

  const copyDiagnostics = useCallback(() => {
    const diag = {
      ts:   new Date().toISOString(),
      core: { status: coreStatus, lastConnected: coreLast, lastCloseCode: coreCode },
      ai:   { status: aiStatus,   lastConnected: aiLast,   lastCloseCode: aiCode },
    };
    navigator.clipboard.writeText(JSON.stringify(diag, null, 2)).catch(() => {});
    setShowConnFlyout(false);
  }, [coreStatus, aiStatus, coreLast, aiLast, coreCode, aiCode]);

  return (
    <div className="flex items-center gap-1.5">
      <div
        className="font-mono-tech text-[9px] tracking-wider"
        style={{ color: backendOnline ? 'hsl(186 100% 50% / 0.6)' : '#ff453a99' }}
      >
        v4.1 · {backendOnline ? 'ONLINE' : 'OFFLINE'}
      </div>

      <div className="relative" ref={flyoutRef}>
        {!bothOnline && (
          <button
            onClick={() => setShowConnFlyout(v => !v)}
            title="Click for connection details"
            className={`flex items-center gap-0.5 font-orbitron text-[7px] px-1 py-px rounded border cursor-pointer transition-opacity hover:opacity-80${badgePulse ? ' animate-pulse' : ''}`}
            style={{ color: badgeColor, borderColor: `${badgeColor}50`, background: `${badgeColor}10` }}
          >
            {!backendOnline && !bothIdle && <WifiOff size={7} />}
            {badgeLabel}
          </button>
        )}

        {showConnFlyout && (
          <div
            className="absolute left-0 top-full mt-1 z-50 rounded border p-3 min-w-[240px]"
            style={{
              background: 'rgba(0,5,20,0.97)',
              borderColor: 'hsl(186 100% 50% / 0.25)',
              boxShadow: '0 8px 32px rgba(0,0,0,0.6)',
            }}
          >
            <div className="font-orbitron text-[9px] text-hud-cyan/60 tracking-widest mb-2">CONNECTION DETAILS</div>

            <div className="flex items-center justify-between mb-1.5">
              <span className="font-mono-tech text-[9px] text-hud-cyan/50">/ws/system</span>
              <div className="flex items-center gap-2">
                <span
                  className="font-orbitron text-[7px] px-1 py-px rounded"
                  style={{ color: statusColor(coreStatus), background: `${statusColor(coreStatus)}18` }}
                >{coreStatus.toUpperCase()}</span>
                <span className="font-mono-tech text-[8px] text-hud-cyan/40">{fmtTime(coreLast)}</span>
                {coreCode !== null && (
                  <span
                    className="font-mono-tech text-[7px]"
                    style={{ color: coreCode === 1000 ? '#636366' : '#ff453a80' }}
                  >
                    {closeCodeLabel(coreCode)}
                  </span>
                )}
              </div>
            </div>

            <div className="flex items-center justify-between mb-3">
              <span className="font-mono-tech text-[9px] text-hud-cyan/50">/ws/ai</span>
              <div className="flex items-center gap-2">
                <span
                  className="font-orbitron text-[7px] px-1 py-px rounded"
                  style={{ color: statusColor(aiStatus), background: `${statusColor(aiStatus)}18` }}
                >{aiStatus.toUpperCase()}</span>
                <span className="font-mono-tech text-[8px] text-hud-cyan/40">{fmtTime(aiLast)}</span>
                {aiCode !== null && (
                  <span
                    className="font-mono-tech text-[7px]"
                    style={{ color: aiCode === 1000 ? '#636366' : '#ff453a80' }}
                  >
                    {closeCodeLabel(aiCode)}
                  </span>
                )}
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => { bumpRetry(); setShowConnFlyout(false); }}
                className="flex-1 font-orbitron text-[8px] px-2 py-1 rounded border border-hud-cyan/30 text-hud-cyan/70 hover:border-hud-cyan/60 hover:text-hud-cyan transition-colors"
              >
                ↺ RETRY
              </button>
              <button
                onClick={copyDiagnostics}
                className="flex-1 font-orbitron text-[8px] px-2 py-1 rounded border border-hud-cyan/20 text-hud-cyan/50 hover:border-hud-cyan/40 hover:text-hud-cyan/80 transition-colors"
              >
                ⎘ COPY DIAG
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function TopBarActions({
  ttsEnabled,
  onToggleTts,
}: {
  ttsEnabled?: boolean;
  onToggleTts?: () => void;
}) {
  const { user, isAuthenticated, logout } = useAuth();
  const alertCount = useAlertStore(s => s.alerts.filter(a => !a.dismissed).length);

  return (
    <div className="flex items-center gap-3 min-w-0 pointer-events-auto">
      <button
        onClick={() => window.dispatchEvent(new CustomEvent('module-activate', { detail: { module: 'alertlog' } }))}
        className="relative flex items-center justify-center w-7 h-7 rounded border border-hud-cyan/20 text-hud-cyan/40 hover:border-hud-cyan/50 hover:text-hud-cyan transition-all"
        title="Alerts"
      >
        <Bell size={12} />
        {alertCount > 0 && (
          <span
            className="absolute -top-1 -right-1 min-w-[14px] h-3.5 rounded-full font-orbitron text-[7px] flex items-center justify-center px-0.5"
            style={{ background: '#ff9f0a', color: '#000' }}
          >
            {alertCount}
          </span>
        )}
      </button>

      <button
        onClick={() => window.dispatchEvent(new CustomEvent('module-activate', { detail: { module: 'plugins' } }))}
        className="flex items-center justify-center w-7 h-7 rounded border border-hud-cyan/20 text-hud-cyan/30 hover:border-hud-cyan/50 hover:text-hud-cyan/70 transition-all"
        title="Settings"
      >
        <Settings size={12} />
      </button>

      <div className="w-px h-5" style={{ background: 'rgba(0,245,255,0.15)' }} />

      {onToggleTts !== undefined && (
        <button
          onClick={onToggleTts}
          title={ttsEnabled ? 'TTS ON — Click to mute' : 'TTS OFF — Click to enable'}
          className={`flex items-center gap-1 px-2 py-0.5 rounded border transition-all duration-200 ${
            ttsEnabled
              ? 'border-hud-green/40 text-hud-green hover:border-hud-green'
              : 'border-hud-cyan/20 text-hud-cyan/30 hover:border-hud-cyan/50 hover:text-hud-cyan/60'
          }`}
        >
          {ttsEnabled ? <Volume2 size={11} /> : <VolumeX size={11} />}
          <span className="font-orbitron text-[8px] tracking-wider">
            {ttsEnabled ? 'TTS ON' : 'TTS OFF'}
          </span>
        </button>
      )}

      {isAuthenticated && user && (
        <div className="flex items-center gap-1.5 pl-3 border-l border-hud-cyan/20">
          <div className="flex items-center gap-1 px-2 py-0.5 rounded border border-hud-cyan/20 bg-hud-cyan/5">
            <User size={9} className="text-hud-cyan/60" />
            <span className="font-orbitron text-[9px] text-hud-cyan/70 tracking-widest uppercase">
              {user.username}
            </span>
            <span
              className="font-orbitron text-[7px] px-1 rounded border ml-1"
              style={{
                borderColor: user.role === 'admin' ? '#ff9f0a50' : '#00f5ff30',
                color:       user.role === 'admin' ? '#ff9f0a'   : '#00f5ff80',
                background:  user.role === 'admin' ? '#ff9f0a10' : '#00f5ff08',
              }}
            >
              {user.role.toUpperCase()}
            </span>
          </div>
          <button
            onClick={logout}
            title="Logout"
            className="text-hud-cyan/30 hover:text-hud-red/80 transition-colors p-1 rounded"
          >
            <LogOut size={10} />
          </button>
        </div>
      )}
    </div>
  );
}

function SystemModeSelector() {
  const { aiMode, setAiMode } = useHudTheme();
  const systemMode: SystemMode = aiMode as SystemMode;

  const modeColors: Record<string, string> = {
    PASSIVE: 'text-hud-cyan border-hud-cyan',
    ACTIVE: 'text-hud-amber border-hud-amber',
    COMBAT: 'text-hud-red border-hud-red',
  };

  const handleSystemModeChange = useCallback((mode: SystemMode) => {
    setAiMode(mode);
    window.dispatchEvent(new CustomEvent('spark:system-mode-change', {
      detail: { mode },
    }));
  }, [setAiMode]);

  return (
    <div className="flex gap-1 pointer-events-auto">
      {(['PASSIVE', 'ACTIVE', 'COMBAT'] as const).map(mode => (
        <button
          key={mode}
          onClick={() => handleSystemModeChange(mode)}
          className={`font-orbitron text-[9px] px-2 py-0.5 rounded border tracking-wider transition-all duration-200 ${systemMode === mode
            ? `${modeColors[mode]} bg-current/10`
            : 'text-hud-cyan/40 border-hud-cyan/20 hover:border-hud-cyan/50'
            }`}
        >
          {mode}
        </button>
      ))}
    </div>
  );
}

export default function TopBar({
  ttsEnabled,
  onToggleTts,
  onMicTranscript
}: {
  ttsEnabled?: boolean;
  onToggleTts?: () => void;
  onMicTranscript?: (transcript: string) => void;
} = {}) {
  const { hudMode, toggleHudMode } = useHudTheme();

  return (
    <header
      className="relative z-20 flex items-center justify-between px-4 py-1.5 animate-boot-down pointer-events-none"
      style={{
        background: 'rgba(0,5,20,0.85)',
        backdropFilter: 'blur(16px)',
        borderBottom: '1px solid hsl(186 100% 50% / 0.3)',
        boxShadow: '0 2px 30px hsl(186 100% 50% / 0.1)',
        animationDelay: '0.1s',
      }}
    >
      <div className="absolute inset-0 pointer-events-none opacity-5"
        style={{ backgroundImage: 'linear-gradient(hsl(186 100% 50%) 1px, transparent 1px), linear-gradient(90deg, hsl(186 100% 50%) 1px, transparent 1px)', backgroundSize: '40px 40px' }} />

      <div className="flex items-center gap-4 min-w-0 pointer-events-auto">
        <div className="flex items-center gap-2">
          <div className="relative">
            <div className="w-8 h-8 rounded-full border-2 border-hud-cyan flex items-center justify-center animate-pulse-glow">
              <Zap size={14} className="text-hud-cyan" />
            </div>
            <div className="absolute inset-0 rounded-full animate-pulse-ring border border-hud-cyan opacity-50" />
          </div>
          <div>
            <div className="font-orbitron text-sm font-bold neon-text tracking-widest">SPARK</div>
            <ConnectionBadge />
          </div>
        </div>

        <SystemModeSelector />

        <div className="pointer-events-auto">
          <HudModeChip mode={hudMode} onToggle={toggleHudMode} />
        </div>
      </div>

      <TopBarClock />

      <TopBarActions ttsEnabled={ttsEnabled} onToggleTts={onToggleTts} />
    </header>
  );
}
