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
  ts:             number;
}

export function useCommanderContext(
  metrics: { cpu: number; ram: number; ping: number },
  activeModule?: string | null,
): CommanderContext {
  const location = useLocation();

  const lastAlert = useAlertStore((s) => {
    const active = s.alerts.filter((a) => !a.dismissed);
    return active.length > 0 ? active[0] : null;
  });

  const runningTools = useToolActivityStore((s) =>
    Array.from(s.pendingTools),
  );

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
    ts:            Date.now(),
  };
}
