import { useState, useCallback } from 'react';
import { Bot, AlertCircle, Clock, RefreshCw, ChevronRight } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiGet, apiPost } from '@/lib/api';

type AgentState = 'IDLE' | 'THINKING' | 'EXECUTING' | 'WAITING' | 'ERROR';

interface AgentInfo {
  name: string;
  description: string;
  state: AgentState;
  queue_depth: number;
  capabilities: string[];
  stats: { completed: number; failed: number; avg_latency_ms: number };
}

interface AgentStatus {
  agents: Record<string, AgentInfo>;
  pending_tasks: number;
}

const stateIcon = {
  IDLE:      <Clock size={11} className="text-hud-cyan/60" />,
  THINKING:  <div className="w-2.5 h-2.5 border border-purple-400 rounded-full animate-spin border-t-transparent" />,
  EXECUTING: <div className="w-2.5 h-2.5 border border-hud-amber rounded-full animate-spin border-t-transparent" />,
  WAITING:   <Clock size={11} className="text-hud-amber" />,
  ERROR:     <AlertCircle size={11} className="text-hud-red" />,
};
const stateColor: Record<AgentState, string> = {
  IDLE: '#00f5ff40', THINKING: '#bf5af2', EXECUTING: '#ffb800', WAITING: '#ffd60a', ERROR: '#ff3b3b',
};

function AgentCard({ id, info }: { id: string; info: AgentInfo }) {
  const busy = info.state !== 'IDLE';
  return (
    <div className={`hud-panel rounded p-2.5 transition-all duration-300 ${busy ? 'border-hud-amber/40' : 'border-hud-cyan/15'}`}>
      <div className="flex items-center gap-2 mb-1">
        {stateIcon[info.state] ?? stateIcon.IDLE}
        <span className="font-rajdhani text-xs text-hud-cyan/90 flex-1 truncate">{info.name}</span>
        <span className="font-orbitron text-[8px]" style={{ color: stateColor[info.state] }}>{info.state}</span>
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
        {info.stats.avg_latency_ms > 0 && (
          <span className="font-mono-tech text-[7px] text-hud-cyan/40">{Math.round(info.stats.avg_latency_ms)}ms avg</span>
        )}
      </div>
    </div>
  );
}

export default function AgentModule() {
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
    setDispatching(true);
    setLastResult(null);
    try {
      const res = await apiPost<{ output?: string; status?: string }>('/api/agents/ask', {
        text: taskInput, wait: false,
      });
      setLastResult(res.output ?? (res.status === 'queued' ? 'Task queued.' : JSON.stringify(res)));
      setTaskInput('');
    } catch (err: any) {
      setLastResult(`Error: ${err.message}`);
    } finally {
      setDispatching(false);
    }
  }, [taskInput]);

  return (
    <div className="flex flex-col gap-3 p-4 h-full overflow-y-auto scrollbar-hud">
      <div className="flex items-center justify-between pb-2 border-b border-hud-cyan/20">
        <div className="flex items-center gap-2">
          <Bot size={14} className="text-hud-cyan" />
          <span className="font-orbitron text-xs tracking-widest neon-text">MULTI-AGENT SYSTEM</span>
          {active > 0 && (
            <span className="font-orbitron text-[8px] px-1.5 py-0.5 rounded bg-hud-amber/20 text-hud-amber border border-hud-amber/40">
              {active} ACTIVE
            </span>
          )}
        </div>
        <button onClick={() => refetch()} className="p-1 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
          <RefreshCw size={10} className={isLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'AGENTS',  value: agentList.length, color: '#00f5ff' },
          { label: 'ACTIVE',  value: active,           color: '#ffb800' },
          { label: 'QUEUED',  value: pending,          color: '#00ff88' },
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
          <div className="font-orbitron text-[9px] text-hud-cyan/60">◈ AGENT NETWORK</div>
          {agentList.map(([id, info]) => <AgentCard key={id} id={id} info={info} />)}
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
          <button onClick={dispatch} disabled={dispatching || !taskInput.trim()}
            className="hud-btn px-2 py-1 flex items-center gap-1 disabled:opacity-40">
            {dispatching
              ? <div className="w-2.5 h-2.5 border border-hud-cyan rounded-full animate-spin border-t-transparent" />
              : <ChevronRight size={11} />}
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
