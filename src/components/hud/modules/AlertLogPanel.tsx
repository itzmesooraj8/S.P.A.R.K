/**
 * AlertLogPanel — HUD module
 * ─────────────────────────────────────────────────────────────────────────────
 * Scrollable history of all system ALERT events with severity filter badges.
 * Opened via BottomDock "ALERTS" button.
 */

import { useState } from 'react';
import { Bell, BellOff, Trash2 } from 'lucide-react';
import { useAlertStore, AlertSeverity } from '@/store/useAlertStore';

const SEV_COLORS: Record<AlertSeverity | 'all', string> = {
  all:      '#00f5ff',
  info:     '#00f5ff',
  warning:  '#ff9f0a',
  critical: '#ff2d55',
};

const SEV_LABELS: Record<AlertSeverity | 'all', string> = {
  all:      'ALL',
  info:     'INFO',
  warning:  'WARN',
  critical: 'CRIT',
};

export default function AlertLogPanel() {
  const { alerts, dismissAlert, clearAll } = useAlertStore();
  const [filter, setFilter] = useState<AlertSeverity | 'all'>('all');

  const shown = alerts.filter(a => filter === 'all' || a.severity === filter);
  const counts = {
    all:      alerts.length,
    info:     alerts.filter(a => a.severity === 'info').length,
    warning:  alerts.filter(a => a.severity === 'warning').length,
    critical: alerts.filter(a => a.severity === 'critical').length,
  };

  return (
    <div className="h-full flex flex-col p-3 gap-2 font-mono-tech">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bell size={12} className="text-hud-cyan/70" />
          <span className="font-orbitron text-[10px] neon-text tracking-widest">SYSTEM ALERTS</span>
          <span className="font-orbitron text-[9px] text-hud-cyan/40">({alerts.length})</span>
        </div>
        <button
          onClick={clearAll}
          className="flex items-center gap-1 text-[8px] text-white/30 hover:text-hud-red/80 transition-colors"
        >
          <Trash2 size={10} />
          CLEAR
        </button>
      </div>

      {/* Severity filter */}
      <div className="flex gap-1">
        {(['all', 'critical', 'warning', 'info'] as const).map(sev => (
          <button
            key={sev}
            onClick={() => setFilter(sev)}
            className="px-2 py-0.5 rounded border text-[8px] tracking-widest font-orbitron transition-all"
            style={{
              borderColor: filter === sev ? SEV_COLORS[sev] : `${SEV_COLORS[sev]}30`,
              color: filter === sev ? SEV_COLORS[sev] : `${SEV_COLORS[sev]}60`,
              background: filter === sev ? `${SEV_COLORS[sev]}15` : 'transparent',
            }}
          >
            {SEV_LABELS[sev]}
            {counts[sev] > 0 && <span className="ml-1 opacity-60">({counts[sev]})</span>}
          </button>
        ))}
      </div>

      {/* Alert list */}
      <div className="flex-1 overflow-y-auto space-y-1.5 pr-1 custom-scroll">
        {shown.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 gap-2 text-white/20">
            <BellOff size={24} />
            <span className="text-[9px] tracking-widest">NO ALERTS</span>
          </div>
        ) : (
          shown.map(alert => {
            const color = SEV_COLORS[alert.severity];
            const isNew = !alert.dismissed && Date.now() - alert.ts < 30_000;
            return (
              <div
                key={alert.id}
                className={`rounded border p-2 transition-opacity ${alert.dismissed ? 'opacity-30' : ''}`}
                style={{
                  borderColor: `${color}30`,
                  background: `${color}08`,
                }}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-1.5 mb-0.5">
                      <div className="w-1.5 h-1.5 rounded-full flex-shrink-0" style={{ background: color }} />
                      <span className="font-orbitron text-[9px] truncate" style={{ color }}>
                        {alert.severity.toUpperCase()}
                      </span>
                      {isNew && (
                        <span className="text-[7px] font-orbitron px-1 rounded border"
                          style={{ borderColor: `${color}50`, color, background: `${color}15` }}>
                          NEW
                        </span>
                      )}
                      <span className="text-[8px] text-white/30 ml-auto flex-shrink-0">
                        {new Date(alert.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                    </div>
                    <div className="font-orbitron text-[9px] text-white/80 leading-tight mb-0.5">
                      {alert.title}
                    </div>
                    {alert.body && (
                      <div className="text-[8px] text-white/40 leading-3.5 line-clamp-2">
                        {alert.body}
                      </div>
                    )}
                    {alert.source && (
                      <div className="text-[7px] text-white/25 mt-0.5">src: {alert.source}</div>
                    )}
                  </div>
                  {!alert.dismissed && (
                    <button
                      onClick={() => dismissAlert(alert.id)}
                      className="text-white/20 hover:text-white/50 transition-colors flex-shrink-0 mt-0.5"
                      title="Dismiss"
                    >
                      ×
                    </button>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
