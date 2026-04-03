/**
 * SPARK Cognitive Dashboard — SPARK-Level AI OS Status Panel
 * Shows: Cognitive Loop, Multi-Agent status, Model Router, Graph Memory,
 *         Threat Intelligence, Self-Evolution proposals.
 */
import { useEffect, useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { apiPost, apiGet } from '@/lib/api';
import { CheckCircle, XCircle, ArrowLeft } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface AgentStatus {
  name: string;
  description: string;
  state: string;
  queue_depth: number;
  capabilities: string[];
  stats: { completed: number; failed: number; avg_latency_ms: number };
}

interface OsStatus {
  version: string;
  codename: string;
  system: { cpu_pct: number; mem_pct: number; mem_gb: number };
  cognitive_loop: {
    running: boolean;
    phase: string;
    cycle_count: number;
    cycle_interval_s: number;
    last_cycle: {
      cycle_id: string;
      completed_at: number;
      anomalies: number;
      confidence: number;
      reflection: string;
      plan_count: number;
    } | null;
  };
  agents: {
    agents: Record<string, AgentStatus>;
    pending_tasks: number;
  };
  models: {
    models: Array<{
      name: string; provider: string; available: boolean;
      task_strengths: string[]; cost_tier: number;
      success_rate: number; avg_latency_ms: number; attempts: number;
    }>;
    local_running: string[];
  };
  memory: { entities: number; relations: number; observations: number; strategic_objectives: number };
  threat: {
    global_risk_score: number; global_risk_level: string;
    total_events: number; hotspots: number; critical_count: number;
    top_threats: Array<{ region: string; score: number; level: string; dominant_threat: string; trend: string }>;
  };
  evolution: { pending_proposals: number };
}

interface EvolutionProposal {
  id: string;
  title: string;
  description: string;
  priority: string;         // HIGH / MEDIUM / LOW
  estimated_impact: string;
  status: string;           // pending / approved / rejected
  created_at?: string;
}

interface ProposalsResponse {
  proposals: EvolutionProposal[];
  total: number;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function riskColor(level: string) {
  switch (level) {
    case 'CRITICAL': return '#ff2d55';
    case 'HIGH':     return '#ff9f0a';
    case 'MEDIUM':   return '#ffd60a';
    default:         return '#30d158';
  }
}

function stateColor(state: string) {
  switch (state) {
    case 'THINKING':  return '#bf5af2';
    case 'EXECUTING': return '#ff9f0a';
    case 'WAITING':   return '#ffd60a';
    case 'ERROR':     return '#ff2d55';
    default:          return '#00f5ff';
  }
}

function phaseColor(phase: string) {
  const map: Record<string, string> = {
    OBSERVING: '#00f5ff', ANALYZING: '#bf5af2', PLANNING: '#ffd60a',
    EXECUTING: '#ff9f0a', REFLECTING: '#30d158', UPDATING: '#0a84ff', IDLE: '#ffffff40',
  };
  return map[phase] || '#ffffff80';
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function HudPanel({ title, children, className = '' }: { title: string; children: React.ReactNode; className?: string }) {
  return (
    <div className={`rounded border border-[#00f5ff20] bg-black/40 backdrop-blur-sm ${className}`}>
      <div className="flex items-center gap-2 px-3 py-2 border-b border-[#00f5ff15]">
        <div className="w-1.5 h-1.5 rounded-full bg-[#00f5ff] animate-pulse" />
        <span className="font-mono text-[10px] tracking-widest uppercase text-[#00f5ff90]">{title}</span>
      </div>
      <div className="p-3">{children}</div>
    </div>
  );
}

function MetricBar({ label, value, max = 100, color = '#00f5ff', unit = '%' }: {
  label: string; value: number; max?: number; color?: string; unit?: string;
}) {
  const pct = Math.min((value / max) * 100, 100);
  return (
    <div className="mb-2">
      <div className="flex justify-between mb-1">
        <span className="font-mono text-[9px] text-white/50 uppercase tracking-widest">{label}</span>
        <span className="font-mono text-[10px]" style={{ color }}>{value.toFixed(1)}{unit}</span>
      </div>
      <div className="h-1 bg-white/10 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function AgentCard({ agent }: { agent: AgentStatus }) {
  return (
    <div className="rounded border border-white/10 p-2 mb-2 bg-white/5">
      <div className="flex items-center justify-between mb-1">
        <span className="font-mono text-[10px] text-white/80">{agent.name.replace('_agent', '')}</span>
        <span className="font-mono text-[9px] px-1.5 py-0.5 rounded" style={{
          background: stateColor(agent.state) + '20', color: stateColor(agent.state),
          border: `1px solid ${stateColor(agent.state)}40`,
        }}>{agent.state}</span>
      </div>
      <div className="font-mono text-[8px] text-white/40 mb-1">{agent.description}</div>
      <div className="flex gap-3 font-mono text-[8px] text-white/50">
        <span>✓ {agent.stats.completed}</span>
        <span style={{ color: agent.stats.failed > 0 ? '#ff2d55' : undefined }}>✗ {agent.stats.failed}</span>
        <span>{agent.stats.avg_latency_ms.toFixed(0)}ms avg</span>
        {agent.queue_depth > 0 && <span className="text-[#ffd60a]">Q:{agent.queue_depth}</span>}
      </div>
    </div>
  );
}

// ─── Main Dashboard ───────────────────────────────────────────────────────────

export default function CognitiveDashboard() {
  const [tick, setTick] = useState(0);
  const qc = useQueryClient();
  const navigate = useNavigate();

  const { data: osData, isLoading } = useQuery<OsStatus>({
    queryKey: ['os-status', tick],
    queryFn: async () => {
      const r = await fetch('/api/os/status');
      if (!r.ok) throw new Error('OS status unavailable');
      return r.json();
    },
    refetchInterval: 8000,
  });

  // ── Evolution proposals ─────────────────────────────────────────────────
  const { data: proposalsData, refetch: refetchProposals } = useQuery<ProposalsResponse>({
    queryKey: ['evolution-proposals'],
    queryFn: () => apiGet<ProposalsResponse>('/api/evolution/proposals'),
    refetchInterval: 15_000,
    retry: 1,
  });

  const approveMut = useMutation({
    mutationFn: (id: string) => apiPost(`/api/evolution/proposals/${id}/approve`, {}),
    onSuccess: () => { refetchProposals(); qc.invalidateQueries({ queryKey: ['os-status'] }); },
  });

  const rejectMut = useMutation({
    mutationFn: (id: string) => apiPost(`/api/evolution/proposals/${id}/reject`, {}),
    onSuccess: () => { refetchProposals(); qc.invalidateQueries({ queryKey: ['os-status'] }); },
  });

  const forceRefresh = useCallback(() => setTick(t => t + 1), []);

  const pendingProposals = proposalsData?.proposals?.filter(p => p.status === 'pending') ?? [];

  if (isLoading || !osData) {
    return (
      <div className="min-h-screen flex items-center justify-center"
        style={{ background: '#000814', color: '#00f5ff' }}>
        <div className="font-mono text-sm tracking-widest animate-pulse">
          ▶ BOOTING SOVEREIGN AI OS...
        </div>
      </div>
    );
  }

  const { system, cognitive_loop, agents, models, memory, threat, evolution } = osData;
  const agentList = Object.values(agents.agents);
  const availableModels = models.models.filter(m => m.available);

  return (
    <div className="min-h-screen p-4 font-mono" style={{
      background: 'radial-gradient(ellipse at top, #00022e 0%, #000814 50%, #000000 100%)',
      color: 'white',
    }}>
      {/* ── Header ── */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <div className="text-xl font-black tracking-widest"
            style={{ color: '#00f5ff', textShadow: '0 0 20px #00f5ff80', fontFamily: 'Orbitron, monospace' }}>
            S.P.A.R.K OS
          </div>
          <div className="text-[9px] tracking-widest text-white/40 uppercase">
            v{osData.version} · {osData.codename} · Sovereign AI Operating System
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <div className="text-[8px] text-white/30 uppercase tracking-widest">Global Risk</div>
            <div className="text-lg font-black" style={{ color: riskColor(threat.global_risk_level) }}>
              {threat.global_risk_score.toFixed(0)}
              <span className="text-[10px] ml-1">{threat.global_risk_level}</span>
            </div>
          </div>
          <button onClick={forceRefresh}
            className="px-2 py-1 rounded border text-[9px] tracking-widest uppercase transition-all hover:bg-white/10"
            style={{ borderColor: '#00f5ff40', color: '#00f5ff80' }}>
            ↻ REFRESH
          </button>
          <button onClick={() => navigate('/')}
            className="px-2 py-1 rounded border text-[9px] tracking-widest uppercase transition-all hover:bg-white/10 flex items-center gap-1"
            style={{ borderColor: '#00f5ff40', color: '#00f5ff80' }}>
            <ArrowLeft size={10} />
            BACK TO HUD
          </button>
        </div>
      </div>

      <div className="grid grid-cols-12 gap-3">

        {/* ── System Vitals ── */}
        <div className="col-span-3">
          <HudPanel title="System Vitals">
            <MetricBar label="CPU" value={system.cpu_pct} color={system.cpu_pct > 80 ? '#ff2d55' : '#00f5ff'} />
            <MetricBar label="Memory" value={system.mem_pct} color={system.mem_pct > 85 ? '#ff2d55' : '#30d158'} />
            <div className="mt-2 text-[9px] text-white/40 font-mono">
              {system.mem_gb.toFixed(1)} GB used
            </div>
          </HudPanel>

          <HudPanel title="Knowledge Graph" className="mt-3">
            {([
              ['Entities',      memory.entities],
              ['Relations',     memory.relations],
              ['Observations',  memory.observations],
              ['Objectives',    memory.strategic_objectives],
            ] as [string, number][]).map(([label, val]) => (
              <div key={label} className="flex justify-between mb-1.5">
                <span className="text-[9px] text-white/40 uppercase tracking-widest">{label}</span>
                <span className="text-[10px] text-[#00f5ff]">{val.toLocaleString()}</span>
              </div>
            ))}
          </HudPanel>

          <HudPanel title="Self-Evolution" className="mt-3">
            <div className="text-[9px] text-white/50 mb-2">
              Human-in-the-loop self-improvement
            </div>
            {pendingProposals.length > 0 ? (
              <div className="space-y-2">
                {pendingProposals.slice(0, 3).map(p => {
                  const priorityColor =
                    p.priority === 'HIGH'   ? '#ff9f0a' :
                    p.priority === 'MEDIUM' ? '#ffd60a' : '#30d158';
                  const isBusy =
                    (approveMut.isPending && approveMut.variables === p.id) ||
                    (rejectMut.isPending  && rejectMut.variables  === p.id);
                  return (
                    <div
                      key={p.id}
                      className="rounded border p-2"
                      style={{ borderColor: `${priorityColor}30`, background: `${priorityColor}08` }}
                    >
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <span className="font-orbitron text-[9px] text-white/80 leading-tight flex-1 min-w-0 truncate">
                          {p.title}
                        </span>
                        <span
                          className="font-orbitron text-[7px] px-1 py-0.5 rounded border flex-shrink-0"
                          style={{ borderColor: `${priorityColor}50`, color: priorityColor }}
                        >
                          {p.priority}
                        </span>
                      </div>
                      {p.description && (
                        <div className="font-mono text-[7px] text-white/35 mb-1.5 leading-3.5 line-clamp-2">
                          {p.description}
                        </div>
                      )}
                      {p.estimated_impact && (
                        <div className="font-mono text-[7px] text-white/25 mb-1.5">
                          Impact: {p.estimated_impact}
                        </div>
                      )}
                      <div className="flex gap-1.5">
                        <button
                          onClick={() => approveMut.mutate(p.id)}
                          disabled={isBusy}
                          className="flex-1 flex items-center justify-center gap-1 py-1 rounded border border-hud-green/40 text-hud-green/80 hover:bg-hud-green/15 hover:border-hud-green/70 transition-all font-orbitron text-[7px] tracking-wider disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          <CheckCircle size={8} />
                          APPROVE
                        </button>
                        <button
                          onClick={() => rejectMut.mutate(p.id)}
                          disabled={isBusy}
                          className="flex-1 flex items-center justify-center gap-1 py-1 rounded border border-hud-red/40 text-hud-red/70 hover:bg-hud-red/10 hover:border-hud-red/60 transition-all font-orbitron text-[7px] tracking-wider disabled:opacity-40 disabled:cursor-not-allowed"
                        >
                          <XCircle size={8} />
                          REJECT
                        </button>
                      </div>
                    </div>
                  );
                })}
                {pendingProposals.length > 3 && (
                  <div className="text-center font-mono text-[8px] text-[#ffd60a80]">
                    +{pendingProposals.length - 3} more proposals
                  </div>
                )}
              </div>
            ) : (
              <div className="text-[9px] text-white/30 text-center py-2">No pending proposals</div>
            )}
          </HudPanel>
        </div>

        {/* ── Cognitive Loop ── */}
        <div className="col-span-3">
          <HudPanel title="Cognitive Loop">
            <div className="flex items-center gap-2 mb-3">
              <div className="w-2 h-2 rounded-full animate-pulse"
                style={{ background: cognitive_loop.running ? '#30d158' : '#ff2d55' }} />
              <span className="text-[10px] text-white/60">
                {cognitive_loop.running ? 'AUTONOMOUS' : 'OFFLINE'}
              </span>
              <span className="ml-auto text-[9px]" style={{ color: phaseColor(cognitive_loop.phase) }}>
                {cognitive_loop.phase}
              </span>
            </div>

            <div className="text-center mb-3">
              <div className="text-3xl font-black" style={{ color: '#00f5ff', textShadow: '0 0 15px #00f5ff60' }}>
                {cognitive_loop.cycle_count}
              </div>
              <div className="text-[8px] text-white/30 uppercase tracking-widest">Cycles Complete</div>
              <div className="text-[8px] text-white/30 mt-1">
                Every {cognitive_loop.cycle_interval_s}s
              </div>
            </div>

            {cognitive_loop.last_cycle && (
              <div className="rounded border border-white/10 bg-white/5 p-2">
                <div className="text-[8px] text-white/50 uppercase tracking-widest mb-1">Last Cycle</div>
                <div className="flex gap-3 text-[9px]">
                  <div>
                    <div className="text-white/30 text-[8px]">Anomalies</div>
                    <div style={{ color: cognitive_loop.last_cycle.anomalies > 0 ? '#ff9f0a' : '#30d158' }}>
                      {cognitive_loop.last_cycle.anomalies}
                    </div>
                  </div>
                  <div>
                    <div className="text-white/30 text-[8px]">Confidence</div>
                    <div style={{ color: '#00f5ff' }}>
                      {(cognitive_loop.last_cycle.confidence * 100).toFixed(0)}%
                    </div>
                  </div>
                  <div>
                    <div className="text-white/30 text-[8px]">Actions</div>
                    <div style={{ color: '#bf5af2' }}>{cognitive_loop.last_cycle.plan_count}</div>
                  </div>
                </div>
                {cognitive_loop.last_cycle.reflection && (
                  <div className="mt-2 text-[8px] text-white/30 leading-4 line-clamp-3">
                    {cognitive_loop.last_cycle.reflection}
                  </div>
                )}
              </div>
            )}
          </HudPanel>
        </div>

        {/* ── Agents ── */}
        <div className="col-span-3">
          <HudPanel title={`Multi-Agent System (${agentList.length} agents)`}>
            <div className="text-[8px] text-white/30 mb-2">
              Pending: {agents.pending_tasks} task{agents.pending_tasks !== 1 ? 's' : ''}
            </div>
            {agentList.map(agent => (
              <AgentCard key={agent.name} agent={agent} />
            ))}
          </HudPanel>
        </div>

        {/* ── Threat Intelligence ── */}
        <div className="col-span-3">
          <HudPanel title="Threat Intelligence">
            <div className="text-center mb-3">
              <div className="text-4xl font-black" style={{
                color: riskColor(threat.global_risk_level),
                textShadow: `0 0 20px ${riskColor(threat.global_risk_level)}60`,
              }}>
                {threat.global_risk_score.toFixed(0)}
              </div>
              <div className="text-[9px] font-black uppercase tracking-widest mt-1"
                style={{ color: riskColor(threat.global_risk_level) }}>
                {threat.global_risk_level}
              </div>
              <div className="flex justify-center gap-4 mt-2 text-[8px] text-white/40">
                <span>{threat.total_events} events</span>
                <span style={{ color: threat.hotspots > 0 ? '#ff9f0a' : undefined }}>
                  {threat.hotspots} hotspots
                </span>
                <span style={{ color: threat.critical_count > 0 ? '#ff2d55' : undefined }}>
                  {threat.critical_count} critical
                </span>
              </div>
            </div>

            <div className="text-[8px] text-white/30 uppercase tracking-widest mb-2">Top Threats</div>
            {threat.top_threats.slice(0, 5).map((t, i) => (
              <div key={i} className="flex items-center gap-2 mb-1.5">
                <div className="w-1 h-1 rounded-full flex-shrink-0"
                  style={{ background: riskColor(t.level) }} />
                <div className="flex-1 min-w-0">
                  <div className="text-[8px] text-white/60 truncate">{t.region}</div>
                  <div className="text-[8px] text-white/30">{t.dominant_threat} · {t.trend}</div>
                </div>
                <div className="text-[9px] font-bold flex-shrink-0"
                  style={{ color: riskColor(t.level) }}>
                  {t.score.toFixed(0)}
                </div>
              </div>
            ))}
            {threat.top_threats.length === 0 && (
              <div className="text-center text-[9px] text-white/20 py-4">
                No active threats detected
              </div>
            )}
          </HudPanel>
        </div>

        {/* ── Model Router ── (full width bottom) */}
        <div className="col-span-12">
          <HudPanel title={`Model Router — ${availableModels.length} providers available`}>
            <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-2">
              {models.models.map(m => (
                <div key={m.name} className={`rounded border p-2 ${m.available ? 'border-white/15 bg-white/5' : 'border-white/5 opacity-40'}`}>
                  <div className="flex items-center gap-1 mb-1">
                    <div className="w-1.5 h-1.5 rounded-full flex-shrink-0"
                      style={{ background: m.available ? '#30d158' : '#ff2d5560' }} />
                    <span className="font-mono text-[8px] text-white/70 truncate">{m.name}</span>
                  </div>
                  <div className="text-[7px] text-white/30 mb-1 uppercase tracking-wide">{m.provider}</div>
                  {m.available && m.attempts > 0 && (
                    <div className="font-mono text-[7px] text-white/40">
                      {(m.success_rate * 100).toFixed(0)}% · {m.avg_latency_ms.toFixed(0)}ms
                    </div>
                  )}
                  <div className="flex flex-wrap gap-0.5 mt-1">
                    {m.task_strengths.slice(0, 3).map(s => (
                      <span key={s} className="text-[6px] px-0.5 rounded"
                        style={{ background: '#00f5ff15', color: '#00f5ff80' }}>
                        {s}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            {availableModels.length === 0 && (
              <div className="text-center text-[9px] text-white/30 py-4">
                ⚠️ No models available — ensure Ollama is running or configure API keys
              </div>
            )}
          </HudPanel>
        </div>

      </div>

      {/* Footer */}
      <div className="mt-4 text-center font-mono text-[8px] text-white/20">
        SPARK Sovereign AI OS · Cognitive Dashboard · Auto-refresh 8s
      </div>
    </div>
  );
}
