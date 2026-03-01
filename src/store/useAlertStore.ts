/**
 * SPARK Alert Store
 * ─────────────────────────────────────────────────────────────────────────────
 * Global Zustand store for system alerts arriving via /ws/system ALERT frames.
 * Keeps last 50 alerts; each has an auto-dismiss flag used by SparkAlertToast.
 */

import { create } from 'zustand';

export type AlertSeverity = 'info' | 'warning' | 'critical';

export interface SparkAlert {
  id: string;
  severity: AlertSeverity;
  title: string;
  body: string;
  source: string;
  ts: number;
  dismissed: boolean;
  toastShown: boolean;
}

interface AlertStore {
  alerts: SparkAlert[];
  addAlert: (alert: Omit<SparkAlert, 'id' | 'dismissed' | 'toastShown'>) => void;
  dismissAlert: (id: string) => void;
  markToastShown: (id: string) => void;
  clearAll: () => void;
}

const MAX_ALERTS = 50;

export const useAlertStore = create<AlertStore>((set) => ({
  alerts: [],

  addAlert: (raw) => set((s) => {
    const alert: SparkAlert = {
      ...raw,
      id: `alert-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
      dismissed: false,
      toastShown: false,
    };
    const alerts = [alert, ...s.alerts].slice(0, MAX_ALERTS);
    return { alerts };
  }),

  dismissAlert: (id) => set((s) => ({
    alerts: s.alerts.map(a => a.id === id ? { ...a, dismissed: true } : a),
  })),

  markToastShown: (id) => set((s) => ({
    alerts: s.alerts.map(a => a.id === id ? { ...a, toastShown: true } : a),
  })),

  clearAll: () => set({ alerts: [] }),
}));
