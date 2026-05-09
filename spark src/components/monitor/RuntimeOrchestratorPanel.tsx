import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Activity, Brain, Cpu, DatabaseZap, Workflow, RefreshCw } from 'lucide-react';
import { apiGet } from '@/lib/api';
import { BasePanel } from './BasePanel';

type RuntimeDashboard = {
  active_intent: string;
  selected_agent: string;
  inference_mode: string;
  task_graph: {
    nodes: number;
    active_node: string | null;
  };
  queue_depth: number;
  runtime_state: string;
  memory_hits: number;
  retrievals: number;
  events: string[];
};

const STATE_COLOR: Record<string, string> = {
  idle: '#6b7280',
  planning: '#fbbf24',
  executing: '#00f5ff',
  completed: '#30d158',
  blocked: '#ff453a',
};

export default function RuntimeOrchestratorPanel({ accentColor = '#00f5ff' }: { accentColor?: string }) {
  const { data, refetch, isFetching } = useQuery<RuntimeDashboard>({
    queryKey: ['runtime-dashboard'],
    queryFn: () => apiGet<RuntimeDashboard>('/api/runtime/dashboard'),
    refetchInterval: 2200,
    staleTime: 1000,
  });

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const stateColor = STATE_COLOR[(data?.runtime_state || '').toLowerCase()] ?? accentColor;

  return (
    <BasePanel
      title="RUNTIME ORCHESTRATOR"
      accentColor={accentColor}
      defaultCollapsed={false}
      badge={data ? (
        <span className="text-[8px] font-mono px-1.5 py-0.5 rounded border" style={{ color: stateColor, borderColor: `${stateColor}30`, background: `${stateColor}10` }}>
          {data.runtime_state.toUpperCase()}
        </span>
      ) : null}
      icon={<Workflow size={10} />}
    >
      <div className="p-3 space-y-3">
        <div className="flex items-center gap-2 text-[9px] font-mono text-white/55 flex-wrap">
          <span className="px-1.5 py-0.5 rounded border border-white/10 bg-white/5 inline-flex items-center gap-1">
            <Brain size={9} /> intent
          </span>
          <span className="px-1.5 py-0.5 rounded border border-white/10 bg-white/5">agent: {data?.selected_agent || 'system_agent'}</span>
          <span className="px-1.5 py-0.5 rounded border border-white/10 bg-white/5">source: {data?.inference_mode || 'local'}</span>
          <button
            onClick={() => refetch()}
            className="ml-auto inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
            disabled={isFetching}
          >
            <RefreshCw size={9} className={isFetching ? 'animate-spin' : ''} />
            refresh
          </button>
        </div>

        <div className="grid grid-cols-2 gap-2">
          <MetricCard label="INTENT" value={data?.active_intent || 'idle'} icon={<Activity size={10} />} color={accentColor} />
          <MetricCard label="GRAPH" value={`${data?.task_graph.nodes ?? 0} nodes`} icon={<Workflow size={10} />} color="#fbbf24" />
          <MetricCard label="QUEUE" value={`${data?.queue_depth ?? 0}`} icon={<Cpu size={10} />} color="#30d158" />
          <MetricCard label="MEMORY" value={`${data?.memory_hits ?? 0} hits`} icon={<DatabaseZap size={10} />} color="#a78bfa" />
        </div>

        <div className="rounded border border-white/10 bg-black/20 p-2">
          <div className="flex items-center justify-between mb-2">
            <span className="text-[9px] font-mono uppercase tracking-widest text-white/45">Event Stream</span>
            <span className="text-[8px] font-mono text-white/30">active: {data?.task_graph.active_node || '—'}</span>
          </div>
          <div className="space-y-1 max-h-36 overflow-y-auto scrollbar-hud pr-1">
            {(data?.events || []).slice(-8).map((event, index) => (
              <div key={`${event}-${index}`} className="flex items-center gap-2 text-[8px] font-mono text-white/45">
                <span className="w-1.5 h-1.5 rounded-full" style={{ background: index === (data?.events || []).length - 1 ? accentColor : 'rgba(255,255,255,0.25)' }} />
                <span>{event.replace(/_/g, ' ')}</span>
              </div>
            ))}
            {(data?.events || []).length === 0 && (
              <div className="text-[8px] font-mono text-white/25">Awaiting runtime events…</div>
            )}
          </div>
        </div>

        <div className="rounded border border-white/10 bg-white/5 p-2">
          <div className="text-[9px] font-mono tracking-widest uppercase text-white/45 mb-1">Runtime Snapshot</div>
          <div className="text-[8px] font-mono text-white/35 leading-relaxed">
            State: {data?.runtime_state || 'idle'} · Retrievals: {data?.retrievals ?? 0} · Nodes: {data?.task_graph.nodes ?? 0}
          </div>
        </div>
      </div>
    </BasePanel>
  );
}

function MetricCard({ label, value, icon, color }: { label: string; value: string; icon: React.ReactNode; color: string }) {
  return (
    <div className="rounded border border-white/10 bg-black/20 p-2 min-h-[62px]">
      <div className="flex items-center gap-1.5 text-[8px] font-mono text-white/45 uppercase tracking-widest">
        <span style={{ color }}>{icon}</span>
        {label}
      </div>
      <div className="mt-1 text-[10px] font-mono text-white/80 break-words leading-tight">
        {value}
      </div>
    </div>
  );
}
