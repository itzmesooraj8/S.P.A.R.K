/**
 * SPARK Tool Activity Store
 * ─────────────────────────────────────────────────────────────────────────────
 * Receives TOOL_EXECUTE and TOOL_RESULT frames from /ws/ai and stores the last
 * 20 tool events for display in ToolActivityPanel.
 */

import { create } from 'zustand';

export type ToolEventType = 'TOOL_EXECUTE' | 'TOOL_RESULT';
export type ToolStatus = 'running' | 'success' | 'error';

export interface ToolEvent {
  id: string;
  type: ToolEventType;
  tool: string;
  arguments?: Record<string, unknown>;
  status?: ToolStatus;
  output?: string;
  error?: string;
  ts: number;
}

interface ToolActivityStore {
  events: ToolEvent[];
  pendingTools: Set<string>; // tool names currently executing
  addExecute: (tool: string, args?: Record<string, unknown>) => void;
  addResult: (tool: string, status: ToolStatus, output?: string, error?: string) => void;
  clearAll: () => void;
}

const MAX_EVENTS = 20;

export const useToolActivityStore = create<ToolActivityStore>((set) => ({
  events: [],
  pendingTools: new Set(),

  addExecute: (tool, args) => set((s) => {
    const event: ToolEvent = {
      id: `tool-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      type: 'TOOL_EXECUTE',
      tool,
      arguments: args,
      status: 'running',
      ts: Date.now(),
    };
    return {
      events: [event, ...s.events].slice(0, MAX_EVENTS),
      pendingTools: new Set([...s.pendingTools, tool]),
    };
  }),

  addResult: (tool, status, output, error) => set((s) => {
    const event: ToolEvent = {
      id: `tool-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      type: 'TOOL_RESULT',
      tool,
      status,
      output,
      error,
      ts: Date.now(),
    };
    const pending = new Set(s.pendingTools);
    pending.delete(tool);
    return {
      events: [event, ...s.events].slice(0, MAX_EVENTS),
      pendingTools: pending,
    };
  }),

  clearAll: () => set({ events: [], pendingTools: new Set() }),
}));
