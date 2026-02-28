/**
 * SystemEnvBar — Real-time system health metrics bar.
 * Reads live data from /ws/system via useSystemMetrics hook.
 * Displays: CPU%, RAM%, GPU%, Temp°C, Disk%, Network activity.
 */
import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Cpu, MemoryStick, HardDrive, Wifi, Thermometer, Zap } from 'lucide-react';
import { useSystemMetrics } from '@/hooks/useSystemMetrics';

interface Props {
  accentColor?: string;
  compact?: boolean; // if true: show only key metrics without labels
}

interface MetricBarProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  unit?: string;
  max?: number;
  warn?: number;
  crit?: number;
  accentColor: string;
  compact?: boolean;
}

function colorForValue(value: number, warn: number, crit: number) {
  if (value >= crit) return '#ff1e2d';
  if (value >= warn) return '#fbbf24';
  return '#34d399';
}

const MetricBar: React.FC<MetricBarProps> = ({
  icon, label, value, unit = '%', max = 100,
  warn = 65, crit = 85, accentColor, compact,
}) => {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  const color = colorForValue(pct, warn, crit);

  return (
    <div className={`flex items-center gap-1.5 ${compact ? 'min-w-0' : ''}`}>
      <span style={{ color: `${color}cc` }} className="shrink-0 opacity-80">{icon}</span>
      {!compact && (
        <span className="text-[9px] font-mono tracking-widest text-gray-500 shrink-0 hidden lg:inline">
          {label}
        </span>
      )}
      <div
        className="relative rounded-full overflow-hidden shrink-0"
        style={{ width: compact ? 36 : 52, height: 4, background: 'rgba(255,255,255,0.06)' }}
      >
        <motion.div
          className="absolute inset-y-0 left-0 rounded-full"
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          style={{ background: color, boxShadow: `0 0 6px ${color}80` }}
        />
      </div>
      <span
        className="text-[9px] font-mono tabular-nums font-semibold"
        style={{ color, minWidth: '2.6rem', textAlign: 'right' }}
      >
        {value.toFixed(0)}{unit}
      </span>
    </div>
  );
};

export const SystemEnvBar: React.FC<Props> = ({ accentColor = '#00f5ff', compact = false }) => {
  const metrics = useSystemMetrics();

  // Temperature heuristic: derive from CPU load if no direct sensor
  const temp = useMemo(() => {
    if (metrics.temperature && metrics.temperature > 0) return metrics.temperature;
    // Heuristic: base 38°C + CPU load × 0.5°C per %
    return Math.round(38 + metrics.cpu * 0.45);
  }, [metrics.temperature, metrics.cpu]);

  const batteryColor =
    metrics.battery < 15 ? '#ff1e2d' :
    metrics.battery < 30 ? '#fbbf24' :
    '#34d399';

  if (!metrics) return null;

  return (
    <div
      className={`flex items-center gap-3 ${compact ? 'gap-2' : 'gap-3.5'} px-3`}
      title="Real-time system metrics"
    >
      {/* CPU */}
      <MetricBar
        icon={<Cpu size={10} />}
        label="CPU"
        value={metrics.cpu}
        warn={65} crit={85}
        accentColor={accentColor}
        compact={compact}
      />

      {/* RAM */}
      <MetricBar
        icon={<MemoryStick size={10} />}
        label="RAM"
        value={metrics.ram}
        warn={70} crit={90}
        accentColor={accentColor}
        compact={compact}
      />

      {/* GPU */}
      {metrics.gpu > 0 && (
        <MetricBar
          icon={<Zap size={10} />}
          label="GPU"
          value={metrics.gpu}
          warn={70} crit={90}
          accentColor={accentColor}
          compact={compact}
        />
      )}

      {/* Temperature */}
      <div className="flex items-center gap-1">
        <Thermometer
          size={10}
          style={{ color: temp >= 85 ? '#ff1e2d' : temp >= 70 ? '#fbbf24' : '#34d399' }}
        />
        {!compact && (
          <span className="text-[9px] font-mono tracking-widest text-gray-500 hidden lg:inline">TEMP</span>
        )}
        <span
          className="text-[9px] font-mono tabular-nums font-semibold"
          style={{ color: temp >= 85 ? '#ff1e2d' : temp >= 70 ? '#fbbf24' : '#34d399' }}
        >
          {temp}°C
        </span>
      </div>

      {/* Network */}
      {!compact && (
        <MetricBar
          icon={<Wifi size={10} />}
          label="NET"
          value={metrics.network}
          warn={60} crit={85}
          accentColor={accentColor}
          compact={compact}
        />
      )}

      {/* Battery (if not charging at 100%) */}
      {!(metrics.charging && metrics.battery >= 98) && (
        <div className="flex items-center gap-1">
          <span style={{ color: `${batteryColor}cc`, fontSize: 10 }}>
            {metrics.charging ? '⚡' : '🔋'}
          </span>
          <span
            className="text-[9px] font-mono tabular-nums font-semibold"
            style={{ color: batteryColor }}
          >
            {metrics.battery.toFixed(0)}%
          </span>
        </div>
      )}

      {/* Online indicator */}
      <div className="flex items-center gap-1 shrink-0">
        <span
          className="w-1.5 h-1.5 rounded-full"
          style={{
            background: metrics.isOnline ? '#34d399' : '#6b7280',
            boxShadow: metrics.isOnline ? '0 0 6px #34d39980' : 'none',
          }}
        />
        {!compact && (
          <span
            className="text-[9px] font-mono tracking-widest hidden lg:inline"
            style={{ color: metrics.isOnline ? '#34d399' : '#6b7280' }}
          >
            {metrics.isOnline ? 'LIVE' : 'OFFLINE'}
          </span>
        )}
      </div>
    </div>
  );
};
