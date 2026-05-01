/**
 * ActionFeedPanel — HUD module
 * ─────────────────────────────────────────────────────────────────────────────
 * Live timeline of SPARK command plans. Each plan shows its intent, query, and
 * collapsible step-by-step execution trace with real-time status updates.
 *
 * Receives data from useActionFeedStore which is fed by /ws/system PLAN+STEP frames.
 */

import { Zap, ChevronDown, ChevronRight, Trash2, Activity } from 'lucide-react';
import { useActionFeedStore, FeedPlan, FeedStep, PlanIntent, StepStatus } from '@/store/useActionFeedStore';

// ── Intent colors + labels ────────────────────────────────────────────────────

const INTENT_META: Record<PlanIntent, { label: string; color: string }> = {
  CHAT:         { label: 'CHAT',    color: '#00f5ff' },
  TASK:         { label: 'TASK',    color: '#bf5af2' },
  GLOBE_QUERY:  { label: 'GLOBE',   color: '#30d158' },
  SYSTEM_QUERY: { label: 'SYSTEM',  color: '#ff9f0a' },
  CREATE_CASE:  { label: 'CASE',    color: '#ff453a' },
  RESEARCH:     { label: 'RSRCH',   color: '#64d2ff' },
  CODE:         { label: 'CODE',    color: '#ffd60a' },
};

const STEP_STATUS_META: Record<StepStatus, { icon: string; color: string }> = {
  pending:  { icon: '○', color: '#ffffff30' },
  running:  { icon: '◉', color: '#00f5ff'  },
  done:     { icon: '✓', color: '#30d158'  },
  failed:   { icon: '✗', color: '#ff453a'  },
  skipped:  { icon: '–', color: '#ffffff30' },
};

function formatTs(ts: number): string {
  // backend sends UNIX seconds (float); JS Date needs milliseconds
  const ms = ts > 9_999_999_999 ? ts : ts * 1000;
  return new Date(ms).toLocaleTimeString('en-US', {
    hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

// ── Step row ──────────────────────────────────────────────────────────────────

function StepRow({ step }: { step: FeedStep }) {
  const { icon, color } = STEP_STATUS_META[step.status];
  const isRunning = step.status === 'running';

  return (
    <div className="flex gap-2 items-start py-0.5">
      {/* Status indicator */}
      <span
        className={`text-[10px] w-3 shrink-0 mt-px ${isRunning ? 'animate-pulse' : ''}`}
        style={{ color }}
      >
        {icon}
      </span>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="font-mono-tech text-[9px] text-white/70 truncate">{step.label}</span>
          {step.tool && (
            <span
              className="font-orbitron text-[7px] px-1 py-px rounded shrink-0"
              style={{ background: `${color}20`, color, border: `1px solid ${color}40` }}
            >
              {step.tool}
            </span>
          )}
        </div>
        {step.result && step.status !== 'running' && (
          <div
            className="font-mono-tech text-[8px] mt-0.5 truncate opacity-60"
            style={{ color }}
          >
            {step.result}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Plan card ─────────────────────────────────────────────────────────────────

function PlanCard({ plan }: { plan: FeedPlan }) {
  const toggleCollapse = useActionFeedStore((s) => s.toggleCollapse);
  const meta = INTENT_META[plan.intent] ?? INTENT_META.CHAT;

  const hasRunning = plan.steps.some((s) => s.status === 'running');
  const hasFailed  = plan.steps.some((s) => s.status === 'failed');
  const allDone    = plan.steps.length > 0 && plan.steps.every(
    (s) => s.status === 'done' || s.status === 'skipped'
  );

  const borderColor = hasFailed
    ? '#ff453a'
    : hasRunning
    ? '#00f5ff'
    : allDone
    ? '#30d158'
    : '#ffffff20';

  return (
    <div
      className="rounded overflow-hidden"
      style={{ border: `1px solid ${borderColor}40`, background: `${borderColor}06` }}
    >
      {/* Plan header */}
      <button
        onClick={() => toggleCollapse(plan.plan_id)}
        className="w-full flex items-center gap-2 px-2 py-1.5 text-left hover:bg-white/5 transition-colors"
      >
        {/* Collapse icon */}
        <span className="text-white/30 shrink-0">
          {plan.collapsed
            ? <ChevronRight size={10} />
            : <ChevronDown size={10} />}
        </span>

        {/* Intent badge */}
        <span
          className="font-orbitron text-[7px] px-1.5 py-px rounded shrink-0"
          style={{ background: `${meta.color}25`, color: meta.color, border: `1px solid ${meta.color}50` }}
        >
          {meta.label}
        </span>

        {/* Query text */}
        <span className="flex-1 font-mono-tech text-[9px] text-white/70 truncate">
          {plan.query}
        </span>

        {/* Timestamp */}
        <span className="font-orbitron text-[7px] text-white/25 shrink-0">
          {formatTs(plan.ts)}
        </span>

        {/* Running pulse */}
        {hasRunning && (
          <span className="w-1.5 h-1.5 rounded-full bg-hud-cyan animate-pulse shrink-0" />
        )}
      </button>

      {/* Steps */}
      {!plan.collapsed && (
        <div
          className="px-3 pb-2 pt-0.5 border-t"
          style={{ borderColor: `${borderColor}30` }}
        >
          {plan.steps.length === 0 ? (
            <span className="font-mono-tech text-[8px] text-white/25">No steps recorded.</span>
          ) : (
            plan.steps.map((step) => <StepRow key={step.idx} step={step} />)
          )}
        </div>
      )}
    </div>
  );
}

// ── Main panel ────────────────────────────────────────────────────────────────

export default function ActionFeedPanel() {
  const { plans, clearAll } = useActionFeedStore();

  const runningCount = plans.filter(
    (p) => p.steps.some((s) => s.status === 'running')
  ).length;

  return (
    <div className="h-full flex flex-col p-3 gap-2 font-mono-tech">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap size={12} className="text-hud-cyan/70" />
          <span className="font-orbitron text-[10px] neon-text tracking-widest">ACTION FEED</span>
          {runningCount > 0 && (
            <span className="flex items-center gap-1">
              <Activity size={8} className="text-hud-cyan animate-pulse" />
              <span className="font-orbitron text-[8px] text-hud-cyan animate-pulse">
                {runningCount} ACTIVE
              </span>
            </span>
          )}
          <span className="font-orbitron text-[9px] text-hud-cyan/40">({plans.length})</span>
        </div>
        {plans.length > 0 && (
          <button
            onClick={clearAll}
            className="flex items-center gap-1 text-[8px] text-white/30 hover:text-hud-red/80 transition-colors"
          >
            <Trash2 size={10} />
            CLEAR
          </button>
        )}
      </div>

      {/* Feed */}
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 custom-scroll">
        {plans.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 gap-2 text-white/20">
            <Zap size={28} />
            <span className="text-[9px] tracking-widest font-orbitron">AWAITING COMMANDS</span>
            <span className="text-[8px] opacity-60">Press Ctrl+Space to issue a command</span>
          </div>
        ) : (
          plans.map((plan) => <PlanCard key={plan.plan_id} plan={plan} />)
        )}
      </div>
    </div>
  );
}
