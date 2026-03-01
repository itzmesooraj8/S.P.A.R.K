import { useState, useEffect, useRef } from 'react';
import { Terminal, Brain, RefreshCw, Activity } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api';

interface CognitiveCycle {
  cycle_id: string;
  completed_at: number;
  anomalies: number;
  confidence: number;
  reflection: string;
  plan_count: number;
}

interface CognitiveStatus {
  running: boolean;
  phase: string;
  cycle_count: number;
  cycle_interval_s: number;
  last_cycle: CognitiveCycle | null;
}

const PHASE_COLORS: Record<string, string> = {
  OBSERVING:  '#00f5ff',
  ANALYZING:  '#bf5af2',
  PLANNING:   '#ffd60a',
  EXECUTING:  '#ff9f0a',
  REFLECTING: '#30d158',
  UPDATING:   '#0a84ff',
  IDLE:       '#ffffff40',
};

interface LogLine {
  id: string;
  color: string;
  text: string;
  ts: number;
  real?: boolean;
}

// Fallback mock reasoning lines  
const MOCK_PHASES = [
  [0, 'INIT: Loading semantic memory layer...'],
  [0, 'LOAD: Contextual embeddings ready'],
  [1, 'OK: Knowledge graph online'],
  [2, 'THINK: Analyzing query intent...'],
  [0, 'RECALL: Fetching related concepts...'],
  [1, 'MATCH: High confidence'],
  [2, 'PLAN: Generating response strategy...'],
  [1, 'EVAL: Logical consistency check PASSED'],
  [1, 'OUTPUT: Response compiled'],
  [0, 'IDLE: Awaiting next input...'],
];

const MOCK_COLORS = ['#00f5ff', '#00ff88', '#ffb800', '#ff3b3b', '#8b00ff'];

export default function ReasoningLogModule() {
  const [logLines, setLogLines] = useState<LogLine[]>([]);
  const [mockIdx, setMockIdx] = useState(0);
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevCycleId = useRef<string | null>(null);
  const prevPhase = useRef<string>('');

  const { data, isLoading, refetch } = useQuery<CognitiveStatus>({
    queryKey: ['cognitive-status'],
    queryFn: () => apiGet<CognitiveStatus>('/api/cognitive/status'),
    refetchInterval: 2000,
    retry: false,
  });

  const phase = data?.phase ?? 'IDLE';
  const cycleCount = data?.cycle_count ?? 0;
  const lastCycle  = data?.last_cycle;
  const isRunning  = data?.running ?? false;
  const phaseColor = PHASE_COLORS[phase] ?? '#00f5ff';

  // Log new real events when phase changes or cycle completes
  useEffect(() => {
    if (!data) return;

    const now = Date.now();

    if (data.phase !== prevPhase.current) {
      prevPhase.current = data.phase;
      setLogLines(prev => [...prev.slice(-100), {
        id:    `phase-${now}`,
        color: PHASE_COLORS[data.phase] ?? '#00f5ff',
        text:  `> [CogLoop] Phase → ${data.phase} | Cycle #${data.cycle_count}`,
        ts:    now,
        real:  true,
      }]);
    }

    if (lastCycle && lastCycle.cycle_id !== prevCycleId.current) {
      prevCycleId.current = lastCycle.cycle_id;
      setLogLines(prev => [
        ...prev.slice(-100),
        {
          id:    `ref-${now}`,
          color: '#00ff88',
          text:  `> [Reflection] ${lastCycle.reflection || 'Cycle complete.'}`,
          ts:    now,
          real:  true,
        },
        {
          id:    `meta-${now}`,
          color: '#00f5ff',
          text:  `> Anomalies: ${lastCycle.anomalies} | Confidence: ${(lastCycle.confidence * 100).toFixed(0)}% | Plans: ${lastCycle.plan_count}`,
          ts:    now,
          real:  true,
        },
      ]);
    }
  }, [data, lastCycle]);

  // Fallback mock when not connected
  useEffect(() => {
    if (isRunning) return;
    const t = setInterval(() => {
      const line = MOCK_PHASES[mockIdx % MOCK_PHASES.length];
      setLogLines(prev => [...prev.slice(-100), {
        id:    `mock-${Date.now()}`,
        color: MOCK_COLORS[line[0] as number],
        text:  line[1] as string,
        ts:    Date.now(),
        real:  false,
      }]);
      setMockIdx(i => i + 1);
    }, 400);
    return () => clearInterval(t);
  }, [isRunning, mockIdx]);

  // Auto-scroll
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [logLines]);

  return (
    <div className="flex flex-col gap-3 p-4 h-full">
      <div className="flex items-center justify-between pb-2 border-b border-hud-cyan/20">
        <div className="flex items-center gap-2">
          <Terminal size={14} className="text-hud-cyan" />
          <span className="font-orbitron text-xs tracking-widest neon-text">AI REASONING LOG</span>
          {isRunning && <div className="ml-1 w-1.5 h-1.5 rounded-full bg-hud-green animate-pulse" />}
        </div>
        <div className="flex items-center gap-2">
          {data && (
            <span className="font-orbitron text-[8px] px-2 py-0.5 rounded border"
              style={{ color: phaseColor, borderColor: `${phaseColor}50`, background: `${phaseColor}10` }}>
              {phase}
            </span>
          )}
          <button onClick={() => refetch()} className="p-1 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
            <RefreshCw size={10} className={isLoading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {/* Stats row when connected */}
      {data && (
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'CYCLES',   value: cycleCount,                         color: '#00f5ff' },
            { label: 'ANOMALIES', value: lastCycle?.anomalies ?? 0,         color: lastCycle?.anomalies ? '#ff3b3b' : '#00ff88' },
            { label: 'CONFIDENCE', value: `${((lastCycle?.confidence ?? 0) * 100).toFixed(0)}%`, color: '#bf5af2' },
          ].map(s => (
            <div key={s.label} className="hud-panel rounded p-1.5 text-center">
              <div className="font-orbitron text-sm font-bold" style={{ color: s.color }}>{s.value}</div>
              <div className="font-orbitron text-[7px] text-hud-cyan/40">{s.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Log window */}
      <div className="flex-1 bg-black/60 rounded border border-hud-cyan/15 p-3 overflow-y-auto scrollbar-hud">
        <div className="font-mono-tech text-[9px] text-hud-green mb-2">
          {isRunning ? 'SPARK COGNITIVE LOOP — ACTIVE' : 'SPARK AI ENGINE — STANDBY'}
        </div>
        <div className="font-mono-tech text-[9px] text-hud-cyan/40 mb-3">
          {'>'} Session started {new Date().toLocaleTimeString()}
        </div>
        {logLines.map((l, i) => (
          <div key={l.id} className={`flex gap-2 leading-5 ${!l.real ? 'opacity-60' : ''}`}>
            <span className="text-hud-cyan/30 shrink-0">{new Date(l.ts).toLocaleTimeString('en', { hour12: false })}</span>
            <span style={{ color: l.color }}>{l.text}</span>
          </div>
        ))}
        <span className="font-mono-tech text-[9px] text-hud-cyan/50 animate-type-cursor">█</span>
        <div ref={bottomRef} />
      </div>

      {/* Phase indicator */}
      {data && (
        <div className="flex items-center gap-2 p-1.5 rounded border border-hud-cyan/15 bg-black/20">
          <Activity size={10} style={{ color: phaseColor }} />
          <span className="font-mono-tech text-[8px]" style={{ color: phaseColor }}>
            {isRunning ? `RUNNING — ${phase} — Cycle #${cycleCount}` : `STOPPED — Last phase: ${phase}`}
          </span>
        </div>
      )}
    </div>
  );
}
