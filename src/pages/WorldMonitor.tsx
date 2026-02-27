import { useEffect, useState } from 'react';
import WorldMonitorFrame from '@/components/WorldMonitorFrame';

const WorldMonitor = () => {
  const [time, setTime] = useState(() => new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  const timeStr = time.toLocaleTimeString('en-US', { hour12: false });
  const dateStr = time.toLocaleDateString('en-US', { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' });

  return (
    <div
      className="flex flex-col w-full h-full overflow-hidden"
      style={{ background: '#000814' }}
    >
      {/* ── SLIM TOP BAR ─────────────────────────────────────────────── */}
      <header className="shrink-0 z-10 border-b border-hud-cyan/20 bg-black/80 backdrop-blur-sm">
        <div className="h-px w-full bg-gradient-to-r from-transparent via-hud-cyan/50 to-transparent" />
        <div className="flex items-center justify-between px-3 py-1.5 gap-3">
          {/* Title */}
          <div className="flex items-center gap-2">
            <span className="inline-block w-1.5 h-1.5 rounded-full bg-hud-cyan animate-pulse shadow-[0_0_5px_hsl(var(--hud-cyan))]" />
            <span className="font-orbitron text-[10px] neon-text tracking-[0.18em] uppercase">S.P.A.R.K · World Monitor</span>
            <span className="hidden sm:block h-3 w-px bg-hud-cyan/20" />
            <span className="hidden sm:block font-mono text-[8px] text-hud-cyan/35 tracking-widest">GLOBAL INTELLIGENCE · LIVE</span>
          </div>
          {/* Status pills */}
          <div className="flex items-center gap-3">
            <Pill dot="green" label="FEED" value="LIVE" />
            <Pill dot="cyan"  label="RELAY" value="NOMINAL" />
            <span className="hidden md:block font-mono text-[7px] text-hud-cyan/20 tracking-widest">OSINT // UNCLASSIFIED</span>
          </div>
          {/* Clock */}
          <div className="flex flex-col items-end shrink-0">
            <span className="font-orbitron text-[12px] neon-text tabular-nums leading-none">{timeStr}</span>
            <span className="font-mono text-[7px] text-hud-cyan/35 tracking-widest uppercase">{dateStr}</span>
          </div>
        </div>
        <div className="h-px w-full bg-gradient-to-r from-transparent via-hud-cyan/15 to-transparent" />
      </header>

      {/* ── WORLD MONITOR (full iframe — WM has its own World/Tech/Finance/Happy tabs) */}
      <main className="flex-1 relative overflow-hidden">
        <WorldMonitorFrame />
      </main>
    </div>
  );
};

function Pill({ dot, label, value }: { dot: 'cyan' | 'green'; label: string; value: string }) {
  const dotCls = dot === 'green'
    ? 'bg-hud-green shadow-[0_0_4px_hsl(var(--hud-green))]'
    : 'bg-hud-cyan shadow-[0_0_4px_hsl(var(--hud-cyan))]';
  const valCls = dot === 'green' ? 'neon-text-green' : 'text-hud-cyan';
  return (
    <div className="flex items-center gap-1">
      <span className={`inline-block w-1.5 h-1.5 rounded-full ${dotCls}`} />
      <span className="font-mono text-[7px] text-hud-cyan/30 tracking-widest">{label}</span>
      <span className={`font-orbitron text-[7px] tracking-widest ${valCls}`}>{value}</span>
    </div>
  );
}

export default WorldMonitor;
