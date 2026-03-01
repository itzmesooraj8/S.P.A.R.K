/**
 * useConnectionStore
 * ─────────────────────────────────────────────────────────────────────────────
 * Singleton Zustand store that tracks backend WebSocket liveness.
 * Updated directly by useSystemMetrics (core) and useAIEvents (ai).
 * Components read this to render "OFFLINE" badges without prop-drilling.
 */

import { create } from 'zustand';

interface ConnectionStore {
  coreOnline: boolean;   // /ws/system — system metrics + PLAN/STEP/ALERT frames
  aiOnline:   boolean;   // /ws/ai    — tool execute/result frames
  setCoreOnline: (v: boolean) => void;
  setAiOnline:   (v: boolean) => void;
}

export const useConnectionStore = create<ConnectionStore>((set) => ({
  coreOnline: false,
  aiOnline:   false,
  setCoreOnline: (v) => set({ coreOnline: v }),
  setAiOnline:   (v) => set({ aiOnline: v }),
}));
