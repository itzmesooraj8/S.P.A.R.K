/**
 * SPARK PANEL — unified AI chat + cognition module
 * Tabs: CHAT (AgentModule) | COGNITION (ReasoningLogModule)
 */
import { useState, useCallback, useEffect, useRef } from 'react';
import { Bot, Brain, AlertCircle, Clock, RefreshCw, ChevronRight, Terminal, Activity } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiGet, apiPost } from '@/lib/api';
import { useContextStore } from '@/store/useContextStore';

/* ── shared types ────────────────────────────────────────────────────────── */
type AgentState = 'IDLE' | 'THINKING' | 'EXECUTING' | 'WAITING' | 'ERROR';
interface AgentInfo {
  name: string; description: string; state: AgentState;
  queue_depth: number; capabilities: string[];
  stats: { completed: number; failed: number; avg_latency_ms: number };
}
interface AgentStatus { agents: Record<string, AgentInfo>; pending_tasks: number; }

interface CognitiveCycle {
  cycle_id: string; completed_at: number; anomalies: number;
  confidence: number; reflection: string; plan_count: number;
}
interface CognitiveStatus {
  running: boolean; phase: string; cycle_count: number;
  cycle_interval_s: number; last_cycle: CognitiveCycle | null;
}

/* ── colours ─────────────────────────────────────────────────────────────── */
const STATE_ICON: Record<AgentState, React.ReactNode> = {
  IDLE:      <Clock size={11} className="text-hud-cyan/60" />,
  THINKING:  <div className="w-2.5 h-2.5 border border-purple-400 rounded-full animate-spin border-t-transparent" />,
  EXECUTING: <div className="w-2.5 h-2.5 border border-hud-amber rounded-full animate-spin border-t-transparent" />,
  WAITING:   <Clock size={11} className="text-hud-amber" />,
  ERROR:     <AlertCircle size={11} className="text-hud-red" />,
};
const STATE_COLOR: Record<AgentState, string> = {
  IDLE: '#00f5ff40', THINKING: '#bf5af2', EXECUTING: '#ffb800', WAITING: '#ffd60a', ERROR: '#ff3b3b',
};
const PHASE_COLORS: Record<string, string> = {
  OBSERVING: '#00f5ff', ANALYZING: '#bf5af2', PLANNING: '#ffd60a',
  EXECUTING: '#ff9f0a', REFLECTING: '#30d158', UPDATING: '#0a84ff', IDLE: '#ffffff40',
};
const MOCK_PHASES: any[] = [];
const MOCK_COLORS: string[] = [];

/* ── Agent card ──────────────────────────────────────────────────────────── */
function AgentCard({ id, info }: { id: string; info: AgentInfo }) {
  const busy = info.state !== 'IDLE';
  return (
    <div className={`hud-panel rounded p-2.5 transition-all duration-300 ${busy ? 'border-hud-amber/40' : 'border-hud-cyan/15'}`}>
      <div className="flex items-center gap-2 mb-1">
        {STATE_ICON[info.state] ?? STATE_ICON.IDLE}
        <span className="font-rajdhani text-xs text-hud-cyan/90 flex-1 truncate">{info.name}</span>
        <span className="font-orbitron text-[8px]" style={{ color: STATE_COLOR[info.state] }}>{info.state}</span>
      </div>
      <div className="font-mono-tech text-[8px] text-hud-cyan/40 truncate mb-1.5">{info.description}</div>
      {info.queue_depth > 0 && (
        <div className="flex items-center gap-1 mb-1">
          <div className="h-0.5 flex-1 rounded-full bg-black/40 overflow-hidden">
            <div className="h-full rounded-full bg-hud-amber animate-pulse" style={{ width: `${Math.min(100, info.queue_depth * 20)}%` }} />
          </div>
          <span className="font-mono-tech text-[8px] text-hud-amber">{info.queue_depth} queued</span>
        </div>
      )}
      <div className="flex gap-2 mt-1">
        <span className="font-mono-tech text-[7px] text-hud-green">{info.stats.completed} done</span>
        {info.stats.failed > 0 && <span className="font-mono-tech text-[7px] text-hud-red">{info.stats.failed} failed</span>}
        {info.stats.avg_latency_ms > 0 && <span className="font-mono-tech text-[7px] text-hud-cyan/40">{Math.round(info.stats.avg_latency_ms)}ms avg</span>}
      </div>
    </div>
  );
}

/* ── CHAT tab ────────────────────────────────────────────────────────────── */
function ChatTab() {
  const { setSelectedItem } = useContextStore();
  const [taskInput, setTaskInput] = useState('');
  const [dispatching, setDispatching] = useState(false);
  const [lastResult, setLastResult] = useState<string | null>(null);

  const { data, isLoading, refetch } = useQuery<AgentStatus>({
    queryKey: ['agents-status'],
    queryFn: () => apiGet<AgentStatus>('/api/agents/status'),
    refetchInterval: 2000,
    retry: false,
  });

  const agents    = data?.agents ?? {};
  const pending   = data?.pending_tasks ?? 0;
  const agentList = Object.entries(agents);
  const active    = agentList.filter(([, a]) => a.state !== 'IDLE').length;

  const dispatch = useCallback(async () => {
    if (!taskInput.trim()) return;
    setDispatching(true); setLastResult(null);
    try {
      const res = await apiPost<{ output?: string; status?: string }>('/api/agents/ask', { text: taskInput, wait: false });
      const resultText = res.output ?? (res.status === 'queued' ? 'Task queued.' : JSON.stringify(res));
      setLastResult(resultText);
      setSelectedItem({ module: 'agent', type: 'task_result', label: taskInput.slice(0, 60), data: { task: taskInput, output: resultText, status: res.status } });
      setTaskInput('');
    } catch (err) {
      setLastResult(`Error: ${err instanceof Error ? err.message : 'Unknown error'}`);
    } finally {
      setDispatching(false);
    }
  }, [taskInput, setSelectedItem]);

  return (
    <div className="flex flex-col gap-3 p-3 h-full overflow-y-auto scrollbar-hud">
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'AGENTS', value: agentList.length, color: '#00f5ff' },
          { label: 'ACTIVE', value: active,           color: '#ffb800' },
          { label: 'QUEUED', value: pending,          color: '#00ff88' },
        ].map(s => (
          <div key={s.label} className="hud-panel rounded p-2 text-center">
            <div className="font-orbitron text-lg font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="font-orbitron text-[7px] text-hud-cyan/50">{s.label}</div>
          </div>
        ))}
      </div>

      {isLoading && agentList.length === 0 ? (
        <div className="text-center font-mono-tech text-[10px] text-hud-cyan/40 py-4">Connecting to agent network...</div>
      ) : agentList.length === 0 ? (
        <div className="text-center font-mono-tech text-[10px] text-hud-red/60 py-4">No agents online. Ensure backend is running.</div>
      ) : (
        <div className="flex flex-col gap-2">
          <div className="flex items-center justify-between">
            <div className="font-orbitron text-[9px] text-hud-cyan/60">◈ AGENT NETWORK</div>
            <button onClick={() => refetch()} className="p-1 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
              <RefreshCw size={10} className={isLoading ? 'animate-spin' : ''} />
            </button>
          </div>
          {agentList.map(([id, info]) => (
            <div key={id} className="cursor-pointer" onClick={() => setSelectedItem({ module: 'agent', type: 'agent', label: `${info.name} [${info.state}]`, data: { id, ...info } })}>
              <AgentCard id={id} info={info} />
            </div>
          ))}
        </div>
      )}

      <div className="mt-auto border-t border-hud-cyan/20 pt-3">
        <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">◈ DISPATCH TASK</div>
        <div className="flex gap-2">
          <input
            value={taskInput}
            onChange={e => setTaskInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && dispatch()}
            placeholder="Natural language task for agents..."
            className="flex-1 bg-black/50 border border-hud-cyan/25 rounded px-2 py-1 font-mono-tech text-[9px] text-hud-cyan/80 placeholder:text-hud-cyan/20 outline-none focus:border-hud-cyan/60"
          />
          <button onClick={dispatch} disabled={dispatching || !taskInput.trim()} className="hud-btn px-2 py-1 flex items-center gap-1 disabled:opacity-40">
            {dispatching ? <div className="w-2.5 h-2.5 border border-hud-cyan rounded-full animate-spin border-t-transparent" /> : <ChevronRight size={11} />}
          </button>
        </div>
        {lastResult && (
          <div className="mt-2 p-2 rounded bg-black/40 border border-hud-cyan/15 font-mono-tech text-[8px] text-hud-green/80 max-h-20 overflow-y-auto scrollbar-hud">
            {lastResult}
          </div>
        )}
      </div>
    </div>
  );
}

/* ── COGNITION tab ───────────────────────────────────────────────────────── */
interface LogLine { id: string; color: string; text: string; ts: number; real?: boolean; }

function CognitionTab() {
  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const [mockIdx, setMockIdx]   = useState(0);
  const bottomRef   = useRef<HTMLDivElement>(null);
  const prevCycleId = useRef<string | null>(null);
  const prevPhase   = useRef<string>('');

  const { data, isLoading, refetch } = useQuery<CognitiveStatus>({
    queryKey: ['cognitive-status'],
    queryFn: () => apiGet<CognitiveStatus>('/api/cognitive/status'),
    refetchInterval: 2000,
    retry: false,
  });

  const phase       = data?.phase ?? 'IDLE';
  const cycleCount  = data?.cycle_count ?? 0;
  const lastCycle   = data?.last_cycle;
  const isRunning   = data?.running ?? false;
  const phaseColor  = PHASE_COLORS[phase] ?? '#00f5ff';

  useEffect(() => {
    if (!data) return;
    const now = Date.now();
    if (data.phase !== prevPhase.current) {
      prevPhase.current = data.phase;
      setLogLines(prev => [...prev.slice(-100), { id: `phase-${now}`, color: PHASE_COLORS[data.phase] ?? '#00f5ff', text: `> [CogLoop] Phase → ${data.phase} | Cycle #${data.cycle_count}`, ts: now, real: true }]);
    }
    if (lastCycle && lastCycle.cycle_id !== prevCycleId.current) {
      prevCycleId.current = lastCycle.cycle_id;
      setLogLines(prev => [...prev.slice(-100),
        { id: `ref-${now}`,  color: '#00ff88', text: `> [Reflection] ${lastCycle.reflection || 'Cycle complete.'}`, ts: now, real: true },
        { id: `meta-${now}`, color: '#00f5ff', text: `> Anomalies: ${lastCycle.anomalies} | Confidence: ${(lastCycle.confidence * 100).toFixed(0)}% | Plans: ${lastCycle.plan_count}`, ts: now, real: true },
      ]);
    }
  }, [data, lastCycle]);

    // Mock interval removed based on user sovereign request

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [logLines]);

  return (
    <div className="flex flex-col gap-3 p-3 h-full">
      {data && (
        <div className="grid grid-cols-3 gap-2 shrink-0">
          {[
            { label: 'CYCLES',     value: cycleCount,                                 color: '#00f5ff' },
            { label: 'ANOMALIES',  value: lastCycle?.anomalies ?? 0,                  color: lastCycle?.anomalies ? '#ff3b3b' : '#00ff88' },
            { label: 'CONFIDENCE', value: `${((lastCycle?.confidence ?? 0) * 100).toFixed(0)}%`, color: '#bf5af2' },
          ].map(s => (
            <div key={s.label} className="hud-panel rounded p-1.5 text-center">
              <div className="font-orbitron text-sm font-bold" style={{ color: s.color }}>{s.value}</div>
              <div className="font-orbitron text-[7px] text-hud-cyan/40">{s.label}</div>
            </div>
          ))}
        </div>
      )}
      <div className="flex items-center justify-between shrink-0">
        <span className="font-orbitron text-[9px] text-hud-cyan/60">◈ COGNITIVE LOOP</span>
        <button onClick={() => refetch()} className="p-1 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
          <RefreshCw size={10} className={isLoading ? 'animate-spin' : ''} />
        </button>
      </div>
      <div className="flex-1 bg-black/60 rounded border border-hud-cyan/15 p-3 overflow-y-auto scrollbar-hud">
        <div className="font-mono-tech text-[9px] text-hud-green mb-2">
          {isRunning ? 'SPARK COGNITIVE LOOP — ACTIVE' : 'SPARK AI ENGINE — STANDBY'}
        </div>
        <div className="font-mono-tech text-[9px] text-hud-cyan/40 mb-3">&gt; Session started {new Date().toLocaleTimeString()}</div>
        {logLines.map(l => (
          <div key={l.id} className={`flex gap-2 leading-5 ${!l.real ? 'opacity-60' : ''}`}>
            <span className="text-hud-cyan/30 shrink-0">{new Date(l.ts).toLocaleTimeString('en', { hour12: false })}</span>
            <span style={{ color: l.color }}>{l.text}</span>
          </div>
        ))}
        <span className="font-mono-tech text-[9px] text-hud-cyan/50 animate-type-cursor">█</span>
        <div ref={bottomRef} />
      </div>
      {data && (
        <div className="flex items-center gap-2 p-1.5 rounded border border-hud-cyan/15 bg-black/20 shrink-0">
          <Activity size={10} style={{ color: phaseColor }} />
          <span className="font-mono-tech text-[8px]" style={{ color: phaseColor }}>
            {isRunning ? `RUNNING — ${phase} — Cycle #${cycleCount}` : `STOPPED — Last: ${phase}`}
          </span>
        </div>
      )}
    </div>
  );
}

/* ── HISTORY tab ─────────────────────────────────────────────────────────── */
interface Observation { id: string; content: string; created_at: string; entity?: string; }

function HistoryTab() {
  const { data, isLoading, refetch } = useQuery<{ observations: Observation[] }>({
    queryKey: ['memory-observations'],
    queryFn: () => apiGet<{ observations: Observation[] }>('/api/memory/observations'),
    refetchInterval: 15_000,
    retry: 1,
  });

  const observations = data?.observations ?? [];

  return (
    <div className="flex flex-col gap-3 p-3 h-full overflow-y-auto scrollbar-hud">
      <div className="flex items-center justify-between shrink-0">
        <span className="font-orbitron text-[9px] text-hud-cyan/60">◈ SESSION HISTORY</span>
        <button onClick={() => refetch()} className="p-1 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
          <RefreshCw size={10} className={isLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      {isLoading && observations.length === 0 && (
        <div className="text-center font-mono-tech text-[10px] text-hud-cyan/40 py-4">Loading history…</div>
      )}

      {!isLoading && observations.length === 0 && (
        <div className="text-center py-8">
          <Clock size={24} className="mx-auto mb-2 text-hud-cyan/20" />
          <p className="font-mono-tech text-[10px] text-hud-cyan/40">No session history yet.</p>
          <p className="font-mono-tech text-[8px] text-hud-cyan/25 mt-1">Memory observations will appear here.</p>
        </div>
      )}

      <div className="flex flex-col gap-1.5">
        {observations.slice(0, 50).map((obs) => (
          <div
            key={obs.id}
            className="hud-panel rounded p-2 border-hud-cyan/10"
          >
            {obs.entity && (
              <span className="font-orbitron text-[7px] text-hud-cyan/50 uppercase tracking-widest">{obs.entity}</span>
            )}
            <p className="font-mono-tech text-[9px] text-hud-cyan/80 leading-relaxed">{obs.content}</p>
            <span className="font-mono-tech text-[7px] text-hud-cyan/30 mt-0.5 block">
              {new Date(obs.created_at).toLocaleString()}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Main export ─────────────────────────────────────────────────────────── */
type Tab = 'chat' | 'cognition' | 'history';

export default function SparkPanel() {
  const [tab, setTab] = useState<Tab>('chat');
  const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'chat',      label: 'CHAT',      icon: <Bot size={10} /> },
    { id: 'cognition', label: 'COGNITION', icon: <Brain size={10} /> },
    { id: 'history',   label: 'HISTORY',   icon: <Clock size={10} /> },
  ];

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex shrink-0 border-b border-hud-cyan/20">
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 font-orbitron text-[9px] tracking-widest transition-colors"
            style={{
              color: tab === t.id ? '#00f5ff' : 'rgba(255,255,255,0.3)',
              borderBottom: tab === t.id ? '2px solid #00f5ff' : '2px solid transparent',
              background: tab === t.id ? 'rgba(0,245,255,0.05)' : 'transparent',
            }}
          >
            {t.icon}{t.label}
          </button>
        ))}
      </div>
      {/* Content */}
      <div className="flex-1 min-h-0">
        {tab === 'chat'      && <ChatTab />}
        {tab === 'cognition' && <CognitionTab />}
        {tab === 'history'   && <HistoryTab />}
      </div>
    </div>
  );
}
