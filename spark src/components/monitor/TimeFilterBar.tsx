/**
 * TimeFilterBar — 1h / 6h / 24h / 48h / 7d event window selector.
 * Compact pill bar, fits inside TopBar or can be used standalone.
 */
import { motion } from 'framer-motion';
import { Clock } from 'lucide-react';
import { useMonitorStore, type TimeWindow } from '@/store/useMonitorStore';

const WINDOWS: { id: TimeWindow; label: string }[] = [
  { id: '1h',  label: '1H'  },
  { id: '6h',  label: '6H'  },
  { id: '24h', label: '24H' },
  { id: '48h', label: '48H' },
  { id: '7d',  label: '7D'  },
];

interface TimeFilterBarProps {
  accentColor?: string;
  compact?: boolean; // hide label, show only clock icon + pills
}

export const TimeFilterBar = ({ accentColor = '#00f5ff', compact = false }: TimeFilterBarProps) => {
  const timeWindow    = useMonitorStore((s) => s.timeWindow);
  const setTimeWindow = useMonitorStore((s) => s.setTimeWindow);

  return (
    <div className="flex items-center gap-1.5 shrink-0">
      {!compact && (
        <Clock size={10} style={{ color: `${accentColor}80` }} className="shrink-0" />
      )}
      <div
        className="flex items-center rounded-md p-0.5 gap-px"
        style={{
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.07)',
        }}
      >
        {WINDOWS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setTimeWindow(id)}
            className="relative px-2 py-1 rounded text-[9px] font-mono font-bold tracking-widest transition-all duration-200"
            style={{
              color: timeWindow === id ? accentColor : 'rgba(255,255,255,0.3)',
            }}
            title={`Show events from last ${label}`}
          >
            {timeWindow === id && (
              <motion.div
                layoutId="time-window-bg"
                className="absolute inset-0 rounded"
                style={{
                  background: `${accentColor}18`,
                  border: `1px solid ${accentColor}30`,
                }}
                transition={{ type: 'spring', stiffness: 420, damping: 32 }}
              />
            )}
            <span className="relative z-10">{label}</span>
          </button>
        ))}
      </div>
    </div>
  );
};
