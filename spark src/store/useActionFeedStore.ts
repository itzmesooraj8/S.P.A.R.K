/**
 * SPARK Action Feed Store
 * ─────────────────────────────────────────────────────────────────────────────
 * Holds live plan execution state received from /ws/system PLAN + STEP frames.
 * Max 10 plans retained (oldest pruned first).
 *
 * Frame shapes expected from backend:
 *   PLAN  → { v:1, type:"PLAN", plan_id, intent, query, steps:[{idx,label,tool,status}], ts }
 *   STEP  → { v:1, type:"STEP", plan_id, step_idx, label, tool, status, result, ts }
 */

import { create } from 'zustand';

export type StepStatus = 'pending' | 'running' | 'done' | 'failed' | 'skipped';
export type PlanIntent = 'CHAT' | 'TASK' | 'GLOBE_QUERY' | 'SYSTEM_QUERY' | 'CREATE_CASE' | 'RESEARCH' | 'CODE';

export interface FeedStep {
  idx: number;
  label: string;
  tool: string | null;
  status: StepStatus;
  result?: string | null;
  ts?: number;
}

export interface FeedPlan {
  plan_id: string;
  intent: PlanIntent;
  query: string;
  steps: FeedStep[];
  ts: number;
  collapsed: boolean;
}

interface ActionFeedStore {
  plans: FeedPlan[];
  addPlan: (plan: Omit<FeedPlan, 'collapsed'>) => void;
  updateStep: (plan_id: string, step_idx: number, patch: Partial<FeedStep>) => void;
  toggleCollapse: (plan_id: string) => void;
  clearAll: () => void;
}

const MAX_PLANS = 10;

export const useActionFeedStore = create<ActionFeedStore>((set) => ({
  plans: [],

  addPlan: (raw) => set((s) => {
    const plan: FeedPlan = { ...raw, collapsed: false };
    const plans = [plan, ...s.plans].slice(0, MAX_PLANS);
    return { plans };
  }),

  updateStep: (plan_id, step_idx, patch) => set((s) => ({
    plans: s.plans.map((p) =>
      p.plan_id !== plan_id
        ? p
        : {
            ...p,
            steps: p.steps.map((step) =>
              step.idx === step_idx ? { ...step, ...patch } : step
            ),
          }
    ),
  })),

  toggleCollapse: (plan_id) => set((s) => ({
    plans: s.plans.map((p) =>
      p.plan_id === plan_id ? { ...p, collapsed: !p.collapsed } : p
    ),
  })),

  clearAll: () => set({ plans: [] }),
}));
