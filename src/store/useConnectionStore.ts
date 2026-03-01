/**
 * useConnectionStore
 * ─────────────────────────────────────────────────────────────────────────────
 * Singleton Zustand store that tracks backend WebSocket liveness.
 * Updated directly by useSystemMetrics (core) and useAIEvents (ai).
 * Components read this to render "OFFLINE" badges without prop-drilling.
 *
 * WsStatus lifecycle:
 *   'connected'   — socket onopen fired, receiving frames
 *   'reconnecting'— socket onclose with abnormal code (1006/1011/etc.), backoff running
 *   'idle'        — socket onclose with code 1000 (Normal Closure) — calm, not an error
 *   'down'        — never connected yet (initial state)
 */

import { create } from 'zustand';

export type WsStatus = 'connected' | 'reconnecting' | 'idle' | 'down';

interface ConnectionStore {
  // ── Derived booleans (for simple badge reads) ──────────────────────────────
  coreOnline: boolean;   // /ws/system — system metrics + PLAN/STEP/ALERT frames
  aiOnline:   boolean;   // /ws/ai    — tool execute/result frames

  // ── Rich status (for connection flyout) ───────────────────────────────────
  coreStatus:         WsStatus;
  aiStatus:           WsStatus;
  coreLastConnected:  number | null;   // Date.now() of last successful onopen
  aiLastConnected:    number | null;
  coreLastCloseCode:  number | null;   // CloseEvent.code of last disconnect
  aiLastCloseCode:    number | null;

  // ── Retry mechanism ────────────────────────────────────────────────────────
  retryNonce: number;   // increment to trigger manual reconnect in WS hooks

  // ── Actions ───────────────────────────────────────────────────────────────
  setCoreOnline: (v: boolean) => void;  // kept for backwards compat
  setAiOnline:   (v: boolean) => void;  // kept for backwards compat

  /**
   * Call on onopen:  setCoreStatus('connected')
   * Call on onclose: setCoreStatus('reconnecting', event.code)
   * Never call 'down' manually — that's the initial state.
   */
  setCoreStatus: (s: WsStatus, closeCode?: number) => void;
  setAiStatus:   (s: WsStatus, closeCode?: number) => void;

  /** Increment retryNonce to force all WS hooks to reconnect immediately. */
  bumpRetry: () => void;
}

export const useConnectionStore = create<ConnectionStore>((set) => ({
  coreOnline:        false,
  aiOnline:          false,
  coreStatus:        'down',
  aiStatus:          'down',
  coreLastConnected: null,
  aiLastConnected:   null,
  coreLastCloseCode: null,
  aiLastCloseCode:   null,
  retryNonce:        0,

  setCoreOnline: (v) => set({ coreOnline: v }),
  setAiOnline:   (v) => set({ aiOnline: v }),

  setCoreStatus: (s, closeCode) => set((state) => {
    // WS close code 1000 = Normal Closure — intentional shutdown, calm idle state
    const effective: WsStatus = (s === 'reconnecting' && closeCode === 1000) ? 'idle' : s;
    return {
      coreStatus:        effective,
      coreOnline:        effective === 'connected',
      coreLastConnected: effective === 'connected' ? Date.now() : state.coreLastConnected,
      coreLastCloseCode: closeCode !== undefined ? closeCode : state.coreLastCloseCode,
    };
  }),

  setAiStatus: (s, closeCode) => set((state) => {
    const effective: WsStatus = (s === 'reconnecting' && closeCode === 1000) ? 'idle' : s;
    return {
      aiStatus:          effective,
      aiOnline:          effective === 'connected',
      aiLastConnected:   effective === 'connected' ? Date.now() : state.aiLastConnected,
      aiLastCloseCode:   closeCode !== undefined ? closeCode : state.aiLastCloseCode,
    };
  }),

  bumpRetry: () => set((state) => ({ retryNonce: state.retryNonce + 1 })),
}));
