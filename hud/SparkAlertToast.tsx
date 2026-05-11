/**
 * SparkAlertToast
 * ─────────────────────────────────────────────────────────────────────────────
 * Floating toast stack (top-right) that consumes useAlertStore and shows
 * incoming ALERT frames with SPARK HUD styling: severity colours, scan-line
 * animation, auto-dismiss after 6 s (10 s for critical).
 */

import { useEffect, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { X, AlertTriangle, Info, AlertCircle } from 'lucide-react';
import { useAlertStore, SparkAlert, AlertSeverity } from '@/store/useAlertStore';

// ── Severity mapping ─────────────────────────────────────────────────────────
const SEV: Record<AlertSeverity, { color: string; border: string; icon: React.ReactNode; label: string; ttl: number }> = {
  info:     { color: '#00f5ff', border: 'border-hud-cyan/40',  icon: <Info       size={12} />, label: 'INFO',     ttl: 6_000  },
  warning:  { color: '#ff9f0a', border: 'border-hud-amber/50', icon: <AlertTriangle size={12} />, label: 'WARN', ttl: 8_000  },
  critical: { color: '#ff2d55', border: 'border-hud-red/60',   icon: <AlertCircle size={12} />, label: 'CRITICAL', ttl: 10_000 },
};

function ToastItem({ alert, onDismiss }: { alert: SparkAlert; onDismiss: () => void }) {
  const sev = SEV[alert.severity];
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    timerRef.current = setTimeout(onDismiss, sev.ttl);
    return () => { if (timerRef.current) clearTimeout(timerRef.current); };
  }, [onDismiss, sev.ttl]);

  return (
    <motion.div
      layout
      initial={{ x: 80, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 80, opacity: 0, scale: 0.9 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className={`relative w-80 rounded border ${sev.border} bg-black/85 backdrop-blur-xl overflow-hidden`}
      style={{ boxShadow: `0 0 20px ${sev.color}25` }}
    >
      {/* Scan-line accent */}
      <div
        className="absolute left-0 top-0 bottom-0 w-0.5 rounded-l"
        style={{ background: sev.color, boxShadow: `0 0 8px ${sev.color}` }}
      />

      {/* Auto-dismiss progress */}
      <motion.div
        className="absolute bottom-0 left-0 h-px"
        style={{ background: sev.color, opacity: 0.4 }}
        initial={{ width: '100%' }}
        animate={{ width: '0%' }}
        transition={{ duration: sev.ttl / 1000, ease: 'linear' }}
      />

      <div className="pl-3 pr-2 py-2">
        {/* Header */}
        <div className="flex items-center justify-between gap-2 mb-1">
          <div className="flex items-center gap-1.5" style={{ color: sev.color }}>
            {sev.icon}
            <span className="font-orbitron text-[9px] tracking-widest">{sev.label}</span>
            {alert.source && (
              <span className="font-mono-tech text-[8px] opacity-50">· {alert.source}</span>
            )}
          </div>
          <button
            onClick={onDismiss}
            className="text-white/30 hover:text-white/70 transition-colors flex-shrink-0"
          >
            <X size={10} />
          </button>
        </div>

        {/* Title */}
        <div className="font-orbitron text-[10px] text-white/90 mb-0.5 leading-tight">
          {alert.title}
        </div>

        {/* Body */}
        {alert.body && (
          <div className="font-mono-tech text-[9px] text-white/50 leading-4 line-clamp-2">
            {alert.body}
          </div>
        )}
      </div>
    </motion.div>
  );
}

// ── Toast container ───────────────────────────────────────────────────────────
export default function SparkAlertToast() {
  const { alerts, dismissAlert, markToastShown } = useAlertStore();

  // Only show alerts that haven't been toasted yet (first arrival)
  const queued = alerts.filter(a => !a.toastShown && !a.dismissed);

  // Mark newly visible ones as shown so they don't reappear after dismiss
  useEffect(() => {
    queued.forEach(a => markToastShown(a.id));
  }, [queued.length]); // eslint-disable-line react-hooks/exhaustive-deps

  // Show last 4 active toasts
  const visible = alerts
    .filter(a => a.toastShown && !a.dismissed)
    .slice(0, 4);

  return (
    <div className="fixed top-14 right-2 z-[999] flex flex-col gap-2 pointer-events-none">
      <AnimatePresence mode="popLayout">
        {visible.map(alert => (
          <div key={alert.id} className="pointer-events-auto">
            <ToastItem
              alert={alert}
              onDismiss={() => dismissAlert(alert.id)}
            />
          </div>
        ))}
      </AnimatePresence>
    </div>
  );
}
