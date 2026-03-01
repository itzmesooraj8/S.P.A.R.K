import { useState, useEffect, useRef } from 'react';
import { Radio, Wifi, WifiOff } from 'lucide-react';

const FEED_SOURCES = ['SYS', 'NET', 'SEC', 'API', 'HW', 'AI'];
const COLORS: Record<string, string> = {
  SYS: '#00f5ff',
  NET: '#0066ff',
  SEC: '#ff3b3b',
  API: '#00ff88',
  HW:  '#ffb800',
  AI:  '#8b00ff',
};

interface StreamLine {
  id: string;
  color: string;
  text: string;
  ts: string;
  src: string;
  realtime?: boolean;
}

const WS_URL = (() => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const port  = import.meta.env.VITE_BACKEND_PORT ?? '8000';
  return `${proto}://${window.location.hostname}:${port}/ws/system`;
})();

// Fallback mock line generator (used when backend is offline)
const FEED_MSGS: Record<string, string[]> = {
  SYS: ['Kernel heartbeat OK', 'Process spawn: worker_' + Math.floor(Math.random() * 999), 'Memory sweep clean', 'CPU governor: balanced'],
  NET: ['Packet recv: ' + Math.floor(Math.random() * 9999) + ' bytes', 'DNS resolved', 'TCP handshake ok', 'TLS 1.3 session'],
  SEC: ['IDS scan: clean', 'Certificate valid', 'Auth token refreshed', 'Firewall rule: PASS'],
  API: ['GET /api/health 200', 'WebSocket ping/pong OK', 'Rate limit OK'],
  HW:  ['SMART status: OK', 'Temp nominal', 'Fan RPM stable'],
  AI:  ['Inference: ' + Math.floor(Math.random() * 50) + 'ms', 'Context tokens: ' + Math.floor(Math.random() * 2048), 'KnowledgeGraph: online'],
};

function mockLine(): StreamLine {
  const src = FEED_SOURCES[Math.floor(Math.random() * FEED_SOURCES.length)];
  const msgs = FEED_MSGS[src];
  return {
    id:    `mock-${Date.now()}-${Math.random()}`,
    color: COLORS[src],
    text:  `[${src}] ${msgs[Math.floor(Math.random() * msgs.length)]}`,
    ts:    new Date().toLocaleTimeString('en', { hour12: false }),
    src,
    realtime: false,
  };
}

export default function DataStreamModule() {
  const [lines, setLines]       = useState<StreamLine[]>([]);
  const [paused, setPaused]     = useState(false);
  const [filter, setFilter]     = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const wsRef     = useRef<WebSocket | null>(null);
  const mockTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  const addLines = (newLines: StreamLine[]) => {
    if (paused) return;
    setLines(prev => [...prev.slice(-300), ...newLines]);
  };

  // Connect to real backend WS
  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>;

    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => setConnected(true);

      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data as string);
          if (msg.type === 'DATASTREAM_BATCH' && Array.isArray(msg.events)) {
            const realLines: StreamLine[] = msg.events.map((e: any) => ({
              id:       `real-${Date.now()}-${Math.random()}`,
              color:    COLORS[e.src] ?? '#00f5ff',
              text:     e.text ?? `[${e.src}] event`,
              ts:       new Date().toLocaleTimeString('en', { hour12: false }),
              src:      e.src ?? 'SYS',
              realtime: true,
            }));
            if (!paused) {
              setLines(prev => [...prev.slice(-300), ...realLines]);
            }
          }
        } catch { /* ignore malformed frames */ }
      };

      ws.onclose = () => { setConnected(false); reconnectTimer = setTimeout(connect, 4000); };
      ws.onerror = () => ws.close();
    };

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      wsRef.current?.close();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Fallback mock events when backend is offline
  useEffect(() => {
    if (connected) {
      if (mockTimer.current) { clearInterval(mockTimer.current); mockTimer.current = null; }
      return;
    }
    if (!paused) {
      mockTimer.current = setInterval(() => {
        const line = mockLine();
        setLines(prev => [...prev.slice(-300), line]);
      }, 300);
    }
    return () => { if (mockTimer.current) clearInterval(mockTimer.current); };
  }, [connected, paused]);

  // Auto-scroll
  useEffect(() => {
    if (!paused) bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [lines, paused]);

  const displayed = filter ? lines.filter(l => l.src === filter) : lines;

  return (
    <div className="flex flex-col gap-3 p-4 h-full">
      <div className="flex items-center justify-between pb-2 border-b border-hud-cyan/20 shrink-0">
        <div className="flex items-center gap-2">
          <Radio size={14} className="text-hud-cyan" />
          <span className="font-orbitron text-xs tracking-widest neon-text">LIVE DATA STREAM</span>
          {connected
            ? <><Wifi size={10} className="text-hud-green" /><span className="font-orbitron text-[7px] text-hud-green">LIVE</span></>
            : <><WifiOff size={10} className="text-hud-amber" /><span className="font-orbitron text-[7px] text-hud-amber">MOCK</span></>
          }
          {!paused && <div className="w-1.5 h-1.5 rounded-full bg-hud-red animate-pulse" />}
        </div>
        <button onClick={() => setPaused(v => !v)}
          className="font-orbitron text-[8px] px-2 py-0.5 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
          {paused ? '▶ RESUME' : '⏸ PAUSE'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex gap-1 shrink-0 flex-wrap">
        <button onClick={() => setFilter(null)}
          className={`font-orbitron text-[8px] px-2 py-0.5 rounded border ${!filter ? 'border-hud-cyan text-hud-cyan' : 'border-hud-cyan/25 text-hud-cyan/40'}`}>
          ALL
        </button>
        {FEED_SOURCES.map(s => (
          <button key={s} onClick={() => setFilter(s === filter ? null : s)}
            className="font-orbitron text-[8px] px-2 py-0.5 rounded border transition-all"
            style={{
              borderColor: filter === s ? COLORS[s] : `${COLORS[s]}40`,
              color:        filter === s ? COLORS[s] : `${COLORS[s]}80`,
              background:   filter === s ? `${COLORS[s]}15` : 'transparent',
            }}>
            {s}
          </button>
        ))}
      </div>

      {/* Stream */}
      <div className="flex-1 overflow-y-auto scrollbar-hud bg-black/50 rounded border border-hud-cyan/15 p-2 font-mono-tech text-[9px]">
        {displayed.map(l => (
          <div key={l.id} className="flex gap-2 leading-4">
            <span className="text-hud-cyan/30 shrink-0">{l.ts}</span>
            <span style={{ color: l.color }} className={l.realtime ? '' : 'opacity-70'}>{l.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Stats bar */}
      <div className="flex gap-3 shrink-0 flex-wrap">
        {FEED_SOURCES.map(s => (
          <div key={s} className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: COLORS[s] }} />
            <span className="font-mono-tech text-[8px]" style={{ color: COLORS[s] }}>
              {s}: {lines.filter(l => l.src === s).length}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
