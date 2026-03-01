/**
 * useCommanderContext
 * ─────────────────────────────────────────────────────────────────────────────
 * Assembles a real-time context snapshot to attach to every /api/commander/run
 * request, giving SPARK full situational awareness about the operator's current
 * HUD state without requiring any manual input.
 *
 * Injected fields:
 *   current_page    — React Router pathname
 *   active_module   — which HUD module is open (optional, passed as prop)
 *   cpu / ram / ping — latest live metrics
 *   threat_level    — derived from cpu heuristic
 *   last_alert      — most recent undismissed alert
 *   running_tools   — list of currently executing tools
 *   ts              — timestamp
 */

import { useMemo } from 'react';
import { useLocation } from 'react-router-dom';
import { useAlertStore } from '@/store/useAlertStore';
import { useToolActivityStore } from '@/store/useToolActivityStore';

export interface CommanderContext {
  current_page:   string;
  active_module?: string | null;
  cpu:            number;
  ram:            number;
  ping_ms:        number;
  threat_level:   string;
  last_alert?:    { title: string; severity: string } | null;
  running_tools:  string[];
}

export function useCommanderContext(
  metrics: { cpu: number; ram: number; ping: number },
  activeModule?: string | null,
): CommanderContext {
  const location = useLocation();

  // Use .find() — returns the same object reference if the alert didn't change.
  // NEVER call .filter() inside a selector; it creates a new array on every snapshot check.
  const lastAlert = useAlertStore((s) =>
    s.alerts.find((a) => !a.dismissed) ?? null,
  );

  // Select the Set reference directly (stable between renders when unchanged).
  // Convert to array OUTSIDE the selector with useMemo to avoid creating a new
  // array on every Zustand snapshot check, which causes an infinite re-render loop.
  const pendingToolsSet = useToolActivityStore((s) => s.pendingTools);
  const runningTools = useMemo(() => Array.from(pendingToolsSet), [pendingToolsSet]);

  return {
    current_page:  location.pathname,
    active_module: activeModule ?? null,
    cpu:           metrics.cpu,
    ram:           metrics.ram,
    ping_ms:       metrics.ping,
    threat_level:  metrics.cpu > 80 ? 'high' : metrics.cpu > 50 ? 'medium' : 'low',
    last_alert:    lastAlert
      ? { title: lastAlert.title, severity: lastAlert.severity }
      : null,
    running_tools: runningTools,
  };
}
