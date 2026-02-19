import { useState, useEffect, useRef } from 'react';
import { Radio } from 'lucide-react';

const FEED_SOURCES = ['SYS', 'NET', 'SEC', 'API', 'HW', 'AI'];
const COLORS = ['#00f5ff', '#0066ff', '#00ff88', '#ffb800', '#8b00ff', '#ff3b3b'];

function generateLine(): { color: string; text: string; ts: string } {
  const src = FEED_SOURCES[Math.floor(Math.random() * FEED_SOURCES.length)];
  const color = COLORS[FEED_SOURCES.indexOf(src)];
  const messages: Record<string, string[]> = {
    SYS: ['Kernel heartbeat OK', 'Memory page flush', 'Process spawn: worker_' + Math.floor(Math.random() * 999), 'CPU governor: balanced'],
    NET: ['Packet recv: ' + Math.floor(Math.random() * 9999) + ' bytes', 'DNS resolved: spark-cdn.io', 'TCP handshake: 192.168.' + Math.floor(Math.random() * 255) + '.' + Math.floor(Math.random() * 255), 'TLS 1.3 session established'],
    SEC: ['Firewall rule hit #' + Math.floor(Math.random() * 999), 'IDS scan: clean', 'Certificate valid', 'Auth token refreshed'],
    API: ['GET /api/status 200 ' + Math.floor(Math.random() * 99) + 'ms', 'POST /api/cmd 201', 'WebSocket ping/pong OK', 'Rate limit: ' + Math.floor(Math.random() * 1000) + '/min'],
    HW: ['Fan RPM: ' + Math.floor(Math.random() * 3000 + 1000), 'Temp sensor: ' + Math.floor(Math.random() * 40 + 40) + '°C', 'Voltage: ' + ((Math.random() * 0.2) + 1.1).toFixed(2) + 'V', 'SMART status: OK'],
    AI: ['Inference: ' + Math.floor(Math.random() * 50 + 10) + 'ms', 'Context tokens: ' + Math.floor(Math.random() * 2048), 'Model: SPARK-7B-Q4', 'Attention heads: 32 active'],
  };
  const opts = messages[src];
  return {
    color,
    text: `[${src}] ${opts[Math.floor(Math.random() * opts.length)]}`,
    ts: new Date().toLocaleTimeString('en', { hour12: false }),
  };
}

export default function DataStreamModule() {
  const [lines, setLines] = useState<ReturnType<typeof generateLine>[]>([]);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (paused) return;
    const interval = setInterval(() => {
      setLines(prev => [...prev.slice(-200), generateLine()]);
    }, 150);
    return () => clearInterval(interval);
  }, [paused]);

  useEffect(() => {
    if (!paused) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines, paused]);

  const displayed = filter ? lines.filter(l => l.text.includes(`[${filter}]`)) : lines;

  return (
    <div className="flex flex-col gap-3 p-4 h-full">
      <div className="flex items-center justify-between pb-2 border-b border-hud-cyan/20 shrink-0">
        <div className="flex items-center gap-2">
          <Radio size={14} className="text-hud-cyan" />
          <span className="font-orbitron text-xs tracking-widest neon-text">LIVE DATA STREAM</span>
          {!paused && <div className="w-1.5 h-1.5 rounded-full bg-hud-red animate-pulse" />}
        </div>
        <button onClick={() => setPaused(v => !v)}
          className="font-orbitron text-[8px] px-2 py-0.5 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
          {paused ? '▶ RESUME' : '⏸ PAUSE'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-1 shrink-0">
        <button onClick={() => setFilter(null)}
          className={`font-orbitron text-[8px] px-2 py-0.5 rounded border ${!filter ? 'border-hud-cyan text-hud-cyan' : 'border-hud-cyan/25 text-hud-cyan/40'}`}>
          ALL
        </button>
        {FEED_SOURCES.map((s, i) => (
          <button key={s} onClick={() => setFilter(s === filter ? null : s)}
            className="font-orbitron text-[8px] px-2 py-0.5 rounded border transition-all"
            style={{
              borderColor: filter === s ? COLORS[i] : `${COLORS[i]}40`,
              color: filter === s ? COLORS[i] : `${COLORS[i]}80`,
              background: filter === s ? `${COLORS[i]}15` : 'transparent',
            }}>
            {s}
          </button>
        ))}
      </div>

      {/* Stream */}
      <div className="flex-1 overflow-y-auto scrollbar-hud bg-black/50 rounded border border-hud-cyan/15 p-2 font-mono-tech text-[9px]">
        {displayed.map((l, i) => (
          <div key={i} className="flex gap-2 leading-4">
            <span className="text-hud-cyan/30 shrink-0">{l.ts}</span>
            <span style={{ color: l.color }}>{l.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Stats bar */}
      <div className="flex gap-4 shrink-0">
        {FEED_SOURCES.map((s, i) => (
          <div key={s} className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: COLORS[i] }} />
            <span className="font-mono-tech text-[8px]" style={{ color: COLORS[i] }}>
              {s}: {lines.filter(l => l.text.includes(`[${s}]`)).length}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
