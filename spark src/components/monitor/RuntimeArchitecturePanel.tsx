import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { RefreshCw } from 'lucide-react';
import { apiGet } from '@/lib/api';
import { BasePanel } from './BasePanel';

type RuntimeModule = {
  name: string;
  purpose: string;
  status: 'online' | 'degraded' | 'planned';
  capabilities: string[];
  signals: Record<string, unknown>;
};

type RuntimeArchitecture = {
  version: string;
  stack_mode: string;
  brain_primary: string;
  modules: RuntimeModule[];
  orchestration: {
    name: string;
    status: 'online' | 'planned' | 'degraded';
    purpose: string;
    agents: string[];
    signals: Record<string, unknown>;
  };
};

const STATUS_COLOR: Record<RuntimeModule['status'], string> = {
  online: '#30d158',
  degraded: '#fbbf24',
  planned: 'rgba(255,255,255,0.35)',
};

export default function RuntimeArchitecturePanel({ accentColor = '#00f5ff' }: { accentColor?: string }) {
  const { data, refetch, isFetching } = useQuery<RuntimeArchitecture>({
    queryKey: ['runtime-architecture'],
    queryFn: () => apiGet<RuntimeArchitecture>('/api/runtime/architecture'),
    refetchInterval: 45_000,
    staleTime: 20_000,
  });

  useEffect(() => {
    void refetch();
  }, [refetch]);

  const modules = data?.modules ?? [];

  return (
    <BasePanel
      title="RUNTIME ARCHITECTURE"
      accentColor={accentColor}
      defaultCollapsed={false}
      badge={data ? (
        <span className="text-[8px] font-mono px-1.5 py-0.5 rounded border" style={{ borderColor: `${accentColor}30`, color: accentColor }}>
          {data.stack_mode.toUpperCase()}
        </span>
      ) : null}
    >
      <div className="p-3 space-y-3">
        {data && (
          <div className="flex flex-wrap items-center gap-2 text-[9px] font-mono text-white/55">
            <span className="px-1.5 py-0.5 rounded border border-white/10 bg-white/5">v{data.version}</span>
            <span className="px-1.5 py-0.5 rounded border border-white/10 bg-white/5">brain: {data.brain_primary}</span>
            <span className="px-1.5 py-0.5 rounded border border-white/10 bg-white/5">agents: {data.orchestration.agents.length}</span>
            <button
              onClick={() => refetch()}
              className="ml-auto inline-flex items-center gap-1 px-1.5 py-0.5 rounded border border-white/10 bg-white/5 hover:bg-white/10 transition-colors"
              disabled={isFetching}
              title="Refresh runtime architecture"
            >
              <RefreshCw size={9} className={isFetching ? 'animate-spin' : ''} />
              refresh
            </button>
          </div>
        )}

        <div className="space-y-2">
          {modules.map((module) => (
            <div key={module.name} className="rounded border border-white/10 bg-black/20 p-2">
              <div className="flex items-center justify-between gap-2">
                <div className="min-w-0">
                  <div className="text-[10px] font-mono font-bold text-white/80 truncate">{module.name}</div>
                  <div className="text-[8px] font-mono text-white/35 leading-relaxed mt-0.5">{module.purpose}</div>
                </div>
                <span
                  className="text-[8px] font-mono px-1.5 py-0.5 rounded border shrink-0"
                  style={{
                    color: STATUS_COLOR[module.status],
                    borderColor: `${STATUS_COLOR[module.status]}30`,
                    background: `${STATUS_COLOR[module.status]}10`,
                  }}
                >
                  {module.status.toUpperCase()}
                </span>
              </div>

              <div className="mt-2 flex flex-wrap gap-1">
                {module.capabilities.map((capability) => (
                  <span key={capability} className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-white/5 border border-white/8 text-white/45">
                    {capability}
                  </span>
                ))}
              </div>
            </div>
          ))}
        </div>

        {data && (
          <div className="rounded border border-white/10 bg-white/5 p-2">
            <div className="text-[9px] font-mono tracking-widest text-white/50 uppercase mb-1">Multi-Agent Orchestration</div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] font-mono text-white/75">{data.orchestration.name}</span>
              <span className="text-[8px] font-mono px-1.5 py-0.5 rounded border" style={{ color: '#00f5ff', borderColor: '#00f5ff30', background: '#00f5ff10' }}>
                {data.orchestration.status.toUpperCase()}
              </span>
            </div>
            <div className="mt-1 text-[8px] font-mono text-white/35 leading-relaxed">{data.orchestration.purpose}</div>
            <div className="mt-2 flex flex-wrap gap-1">
              {data.orchestration.agents.map((agent) => (
                <span key={agent} className="text-[8px] font-mono px-1.5 py-0.5 rounded bg-black/20 border border-white/8 text-white/45">
                  {agent}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </BasePanel>
  );
}
