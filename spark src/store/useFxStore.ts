/**
 * useFxStore
 * ─────────────────────────────────────────────────────────────────────────────
 * Receives ROUTINE_FX frames from /ws/system (via useSystemMetrics) and
 * queues them for consumption by layout components.
 *
 * Producer: useSystemMetrics → watches "ROUTINE_FX" WS frames → pushFx()
 * Consumer: HudLayout → processes queue items → openModule / navigate / modes
 *
 * FX tokens (from spark_core/agents/routines.py):
 *   NAVIGATE_GLOBE        → navigate('/globe-monitor')
 *   NAVIGATE_ALERTS       → openModule('alertlog')
 *   NAVIGATE_TOOLS        → openModule('tools')
 *   NAVIGATE_ACTIONFEED   → openModule('actionfeed')
 *   FOCUS_MODE_ON         → setFocusMode(true)
 *   FOCUS_MODE_OFF        → setFocusMode(false)
 */

import { create } from 'zustand';

export interface FxItem {
  id:    string;
  fx:    string;
  args?: Record<string, unknown>;
}

interface FxStore {
  queue:     FxItem[];
  focusMode: boolean;

  pushFx:      (fx: string, args?: Record<string, unknown>) => void;
  consumeFx:   (id: string) => void;
  setFocusMode:(v: boolean) => void;
}

export const useFxStore = create<FxStore>((set) => ({
  queue:     [],
  focusMode: false,

  pushFx: (fx, args) =>
    set((s) => ({
      queue: [...s.queue, { id: `${fx}-${Date.now()}`, fx, args }],
    })),

  consumeFx: (id) =>
    set((s) => ({ queue: s.queue.filter((item) => item.id !== id) })),

  setFocusMode: (v) => set({ focusMode: v }),
}));
