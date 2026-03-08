/**
 * TELEMETRY — unified system metrics + live event stream
 * Tabs: LIVE (DataStreamModule) | METRICS (AnalyticsModule)
 */
import { useState, useEffect, useRef, useMemo } from 'react';
import { Radio, Wifi, WifiOff, BarChart2 } from 'lucide-react';
import { AreaChart, Area, BarChart, Bar, RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';
import { useSystemMetrics } from '@/hooks/useSystemMetrics';

/* ── DataStream constants ────────────────────────────────────────────────── */
const FEED_SOURCES = ['SYS', 'NET', 'SEC', 'API', 'HW', 'AI'];
const COLORS: Record<string, string> = {
  SYS: '#00f5ff', NET: '#0066ff', SEC: '#ff3b3b', API: '#00ff88', HW: '#ffb800', AI: '#8b00ff',
};

interface StreamLine {
  id: string; color: string; text: string; ts: string; src: string; realtime?: boolean;
}

const WS_URL = (() => {
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const port  = import.meta.env.VITE_BACKEND_PORT ?? '8000';
  return `${proto}://${window.location.hostname}:${port}/ws/system`;
})();

const FEED_MSGS: Record<string, string[]> = {
  SYS: ['Kernel heartbeat OK', 'Memory sweep clean', 'CPU governor: balanced'],
  NET: ['Packet recv: OK', 'DNS resolved', 'TCP handshake ok', 'TLS 1.3 session'],
  SEC: ['IDS scan: clean', 'Certificate valid', 'Auth token refreshed'],
  API: ['GET /api/health 200', 'WebSocket ping/pong OK'],
  HW:  ['SMART status: OK', 'Temp nominal', 'Fan RPM stable'],
  AI:  ['Inference: nominal', 'Context tokens OK', 'KnowledgeGraph: online'],
};

function mockLine(): StreamLine {
  const src  = FEED_SOURCES[Math.floor(Math.random() * FEED_SOURCES.length)];
  const msgs = FEED_MSGS[src];
  return {
    id: `mock-${Date.now()}-${Math.random()}`, color: COLORS[src],
    text: `[${src}] ${msgs[Math.floor(Math.random() * msgs.length)]}`,
    ts: new Date().toLocaleTimeString('en', { hour12: false }), src, realtime: false,
  };
}

/* ── LIVE tab ────────────────────────────────────────────────────────────── */
function LiveTab() {
  const [lines, setLines]     = useState<StreamLine[]>([]);
  const [paused, setPaused]   = useState(false);
  const [filter, setFilter]   = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const wsRef     = useRef<WebSocket | null>(null);
  const mockTimer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let reconnectTimer: ReturnType<typeof setTimeout>;
    const connect = () => {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onopen = () => setConnected(true);
      ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data as string);
          if (msg.type === 'DATASTREAM_BATCH' && Array.isArray(msg.events) && !paused) {
            const realLines: StreamLine[] = msg.events.map((e: Record<string, unknown>) => ({
              id: `real-${Date.now()}-${Math.random()}`, color: COLORS[e.src as string] ?? '#00f5ff',
              text: e.text ?? `[${e.src}] event`, ts: new Date().toLocaleTimeString('en', { hour12: false }),
              src: (e.src as string) ?? 'SYS', realtime: true,
            }));
            setLines(prev => [...prev.slice(-300), ...realLines]);
          }
        } catch { /* ignore malformed frames */ }
      };
      ws.onclose = () => { setConnected(false); reconnectTimer = setTimeout(connect, 4000); };
      ws.onerror = () => ws.close();
    };
    connect();
    return () => { clearTimeout(reconnectTimer); wsRef.current?.close(); };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (connected) { if (mockTimer.current) { clearInterval(mockTimer.current); mockTimer.current = null; } return; }
    if (!paused) {
      mockTimer.current = setInterval(() => {
        setLines(prev => [...prev.slice(-300), mockLine()]);
      }, 300);
    }
    return () => { if (mockTimer.current) clearInterval(mockTimer.current); };
  }, [connected, paused]);

  useEffect(() => { if (!paused) bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [lines, paused]);

  const displayed = filter ? lines.filter(l => l.src === filter) : lines;

  return (
    <div className="flex flex-col gap-2 p-3 h-full">
      <div className="flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2">
          {connected ? <><Wifi size={10} className="text-hud-green" /><span className="font-orbitron text-[7px] text-hud-green">LIVE</span></> : <><WifiOff size={10} className="text-hud-amber" /><span className="font-orbitron text-[7px] text-hud-amber">MOCK</span></>}
          {!paused && <div className="w-1.5 h-1.5 rounded-full bg-hud-red animate-pulse" />}
        </div>
        <button onClick={() => setPaused(v => !v)} className="font-orbitron text-[8px] px-2 py-0.5 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
          {paused ? '▶ RESUME' : '⏸ PAUSE'}
        </button>
      </div>
      <div className="flex gap-1 shrink-0 flex-wrap">
        <button onClick={() => setFilter(null)} className={`font-orbitron text-[8px] px-2 py-0.5 rounded border ${!filter ? 'border-hud-cyan text-hud-cyan' : 'border-hud-cyan/25 text-hud-cyan/40'}`}>ALL</button>
        {FEED_SOURCES.map(s => (
          <button key={s} onClick={() => setFilter(s === filter ? null : s)}
            className="font-orbitron text-[8px] px-2 py-0.5 rounded border transition-all"
            style={{ borderColor: filter === s ? COLORS[s] : `${COLORS[s]}40`, color: filter === s ? COLORS[s] : `${COLORS[s]}80`, background: filter === s ? `${COLORS[s]}15` : 'transparent' }}>
            {s}
          </button>
        ))}
      </div>
      <div className="flex-1 overflow-y-auto scrollbar-hud bg-black/50 rounded border border-hud-cyan/15 p-2 font-mono-tech text-[9px]">
        {displayed.map(l => (
          <div key={l.id} className="flex gap-2 leading-4">
            <span className="text-hud-cyan/30 shrink-0">{l.ts}</span>
            <span style={{ color: l.color }} className={l.realtime ? '' : 'opacity-70'}>{l.text}</span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="flex gap-3 shrink-0 flex-wrap">
        {FEED_SOURCES.map(s => (
          <div key={s} className="flex items-center gap-1">
            <div className="w-1.5 h-1.5 rounded-full" style={{ background: COLORS[s] }} />
            <span className="font-mono-tech text-[8px]" style={{ color: COLORS[s] }}>{s}: {lines.filter(l => l.src === s).length}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Radar constant ──────────────────────────────────────────────────────── */
const RADAR_DATA = [
  { subject: 'CPU', A: 72 }, { subject: 'RAM', A: 68 },
  { subject: 'GPU', A: 55 }, { subject: 'NET', A: 83 },
  { subject: 'DISK', A: 45 }, { subject: 'TEMP', A: 62 },
];

/* ── METRICS tab ─────────────────────────────────────────────────────────── */
function MetricsTab() {
  const metrics = useSystemMetrics();

  const recentLoad = useMemo(() => {
    const history = metrics.cpuHistory ?? [];
    if (history.length === 0) return [];
    const step = Math.max(1, Math.floor(history.length / 7));
    return Array.from({ length: 7 }, (_, i) => {
      const entry = history[Math.min(i * step, history.length - 1)];
      return { day: `T-${(6 - i) * step}`, cpu: Math.round(entry?.value ?? 0), ram: Math.round(metrics.ram), net: Math.round(metrics.network ?? 0) };
    });
  }, [metrics.cpuHistory, metrics.ram, metrics.network]);

  return (
    <div className="flex flex-col gap-3 p-3 h-full overflow-y-auto scrollbar-hud">
      <div className="hud-panel rounded p-3">
        <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">REAL-TIME PERFORMANCE</div>
        <ResponsiveContainer width="100%" height={90}>
          <AreaChart data={metrics.cpuHistory}>
            <defs>
              <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00f5ff" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#00f5ff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" hide /><YAxis domain={[0, 100]} hide />
            <Tooltip contentStyle={{ background: '#00050f', border: '1px solid #00f5ff33', fontSize: '10px', fontFamily: 'Orbitron' }} labelStyle={{ color: '#00f5ff' }} />
            <Area type="monotone" dataKey="value" stroke="#00f5ff" strokeWidth={2} fill="url(#cpuGrad)" dot={false} name="CPU" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="hud-panel rounded p-3">
        <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">LOAD ANALYSIS</div>
        <ResponsiveContainer width="100%" height={90}>
          <BarChart data={recentLoad} barCategoryGap="30%">
            <XAxis dataKey="day" tick={{ fill: '#00f5ff', fontSize: 8, fontFamily: 'Orbitron' }} axisLine={false} tickLine={false} />
            <YAxis hide domain={[0, 100]} />
            <Tooltip contentStyle={{ background: '#00050f', border: '1px solid #00f5ff33', fontSize: '10px', fontFamily: 'Orbitron' }} />
            <Bar dataKey="cpu" fill="#00f5ff" fillOpacity={0.7} radius={[2, 2, 0, 0]} name="CPU" />
            <Bar dataKey="ram" fill="#0066ff" fillOpacity={0.7} radius={[2, 2, 0, 0]} name="RAM" />
            <Bar dataKey="net" fill="#00ff88" fillOpacity={0.7} radius={[2, 2, 0, 0]} name="NET" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="hud-panel rounded p-3">
        <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">SYSTEM PROFILE RADAR</div>
        <ResponsiveContainer width="100%" height={140}>
          <RadarChart data={RADAR_DATA}>
            <PolarGrid stroke="#00f5ff" strokeOpacity={0.2} />
            <PolarAngleAxis dataKey="subject" tick={{ fill: '#00f5ff', fontSize: 9, fontFamily: 'Orbitron' }} />
            <Radar dataKey="A" stroke="#00f5ff" fill="#00f5ff" fillOpacity={0.2} strokeWidth={2} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'CPU AVG',  value: `${Math.round(metrics.cpu)}%`,        color: '#00f5ff' },
          { label: 'RAM USED', value: `${Math.round(metrics.ram)}%`,        color: '#0066ff' },
          { label: 'LATENCY',  value: `${metrics.ping}ms`,                  color: '#0066ff' },
          { label: 'UPTIME',   value: '99.97%',                              color: '#00ff88' },
          { label: 'REQUESTS', value: '2.4K/s',                             color: '#00f5ff' },
          { label: 'THREADS',  value: metrics.processes.toString(),          color: '#8b00ff' },
        ].map(s => (
          <div key={s.label} className="hud-panel rounded p-2 text-center">
            <div className="font-orbitron text-base font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="font-orbitron text-[7px] text-hud-cyan/50 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Main export ─────────────────────────────────────────────────────────── */
type Tab = 'live' | 'metrics';

export default function TelemetryModule() {
  const [tab, setTab] = useState<Tab>('live');
  const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'live',    label: 'LIVE',    icon: <Radio size={10} /> },
    { id: 'metrics', label: 'METRICS', icon: <BarChart2 size={10} /> },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="flex shrink-0 border-b border-hud-cyan/20">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 font-orbitron text-[9px] tracking-widest transition-colors"
            style={{
              color: tab === t.id ? '#00f5ff' : 'rgba(255,255,255,0.3)',
              borderBottom: tab === t.id ? '2px solid #00f5ff' : '2px solid transparent',
              background: tab === t.id ? 'rgba(0,245,255,0.05)' : 'transparent',
            }}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0">
        {tab === 'live'    && <LiveTab />}
        {tab === 'metrics' && <MetricsTab />}
      </div>
    </div>
  );
}
