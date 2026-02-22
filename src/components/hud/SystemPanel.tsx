import { useSystemMetrics } from '@/hooks/useSystemMetrics';
import { useDevState } from '@/hooks/useDevState';
import { Cpu, MemoryStick, Zap, Wifi, Battery, Thermometer, Shield, Lock, AlertTriangle, Terminal } from 'lucide-react';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { useState } from 'react';

interface GaugeProps {
  value: number;
  max?: number;
  color: string;
  size?: number;
}

function RadialGauge({ value, max = 100, color, size = 56 }: GaugeProps) {
  const pct = value / max;
  const r = (size - 8) / 2;
  const circ = 2 * Math.PI * r;
  const dash = pct * circ;
  const cx = size / 2;
  const cy = size / 2;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={3} opacity={0.15} />
      <circle cx={cx} cy={cy} r={r} fill="none" stroke={color} strokeWidth={3}
        strokeDasharray={`${dash} ${circ - dash}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${cx} ${cy})`}
        style={{ filter: `drop-shadow(0 0 4px ${color})`, transition: 'stroke-dasharray 0.5s ease' }}
      />
      <text x={cx} y={cy + 1} textAnchor="middle" dominantBaseline="middle"
        fill={color} fontSize={size < 40 ? 8 : 10}
        fontFamily="'Orbitron', monospace" fontWeight="600">
        {Math.round(value)}%
      </text>
    </svg>
  );
}

interface MetricRowProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  unit?: string;
  color: string;
  history: { value: number; time: number }[];
  warning?: boolean;
}

function MetricRow({ icon, label, value, unit = '%', color, history, warning }: MetricRowProps) {
  return (
    <div className={`p-2 rounded border transition-all duration-300 ${warning ? 'border-hud-amber/50 bg-hud-amber/5' : 'border-hud-cyan/15 bg-hud-cyan/3'}`}>
      <div className="flex items-center gap-2 mb-1.5">
        <div style={{ color }}>{icon}</div>
        <span className="font-orbitron text-[9px] tracking-wider text-hud-cyan/70 flex-1">{label}</span>
        <span className="font-orbitron text-[10px] font-bold" style={{ color }}>
          {Math.round(value)}{unit}
        </span>
        {warning && <AlertTriangle size={9} className="text-hud-amber" />}
      </div>
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1 rounded-full bg-hud-cyan/10 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${value}%`, background: color, boxShadow: `0 0 4px ${color}` }}
          />
        </div>
        <div className="w-16 h-6">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history} margin={{ top: 0, right: 0, bottom: 0, left: 0 }}>
              <defs>
                <linearGradient id={`grad-${label}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor={color} stopOpacity={0.4} />
                  <stop offset="100%" stopColor={color} stopOpacity={0} />
                </linearGradient>
              </defs>
              <Area type="monotone" dataKey="value" stroke={color} strokeWidth={1}
                fill={`url(#grad-${label})`} dot={false} isAnimationActive={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

interface Props {
  metrics: ReturnType<typeof useSystemMetrics>;
}

export default function SystemPanel({ metrics }: Props) {
  const [expandedSections, setExpandedSections] = useState({ resources: true, security: true, environment: true, sandbox: true });
  const toggleSection = (k: keyof typeof expandedSections) =>
    setExpandedSections(p => ({ ...p, [k]: !p[k] }));

  const { sandbox_state } = useDevState();

  const threatColors = { low: '#00ff88', medium: '#ffb800', high: '#ff3b3b' };
  const threatColor = threatColors[metrics.threatLevel];

  return (
    <div className="flex flex-col h-full gap-2 overflow-y-auto scrollbar-hud p-2 animate-boot-left" style={{ animationDelay: '0.3s' }}>
      {/* Panel header */}
      <div className="flex items-center justify-between pb-1 border-b border-hud-cyan/20">
        <span className="font-orbitron text-[9px] tracking-widest neon-text">SYS INTELLIGENCE</span>
        <div className="flex gap-1">
          <div className="w-1.5 h-1.5 rounded-full bg-hud-green animate-pulse" />
          <span className="font-mono-tech text-[8px] text-hud-green/80">NOMINAL</span>
        </div>
      </div>

      {/* Resource Monitors */}
      <div>
        <button
          onClick={() => toggleSection('resources')}
          className="w-full flex items-center justify-between mb-1.5"
        >
          <span className="font-orbitron text-[8px] tracking-widest text-hud-cyan/60">◈ RESOURCES</span>
          <span className="font-mono-tech text-[8px] text-hud-cyan/40">{expandedSections.resources ? '▼' : '▶'}</span>
        </button>
        {expandedSections.resources && (
          <div className="flex flex-col gap-1.5">
            <MetricRow icon={<Cpu size={11} />} label="CPU" value={metrics.cpu}
              color="#00f5ff" history={metrics.cpuHistory} warning={metrics.cpu > 85} />
            <MetricRow icon={<MemoryStick size={11} />} label="RAM" value={metrics.ram}
              color="#0066ff" history={metrics.ramHistory} warning={metrics.ram > 80} />
            <MetricRow icon={<Zap size={11} />} label="GPU" value={metrics.gpu}
              color="#8b00ff" history={metrics.gpuHistory} warning={metrics.gpu > 90} />
            <MetricRow icon={<Wifi size={11} />} label="NETWORK" value={metrics.network}
              color="#00ff88" history={metrics.networkHistory} />
          </div>
        )}
      </div>

      {/* Battery */}
      <div className="p-2 rounded border border-hud-cyan/15">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1.5">
            <Battery size={11} className={metrics.charging ? 'text-hud-green' : 'text-hud-amber'} />
            <span className="font-orbitron text-[9px] text-hud-cyan/70">BATTERY</span>
          </div>
          <span className="font-orbitron text-[10px]" style={{ color: metrics.charging ? '#00ff88' : '#ffb800' }}>
            {Math.round(metrics.battery)}% {metrics.charging ? '⚡' : ''}
          </span>
        </div>
        <div className="relative h-2 rounded-full bg-hud-cyan/10 overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-1000"
            style={{
              width: `${metrics.battery}%`,
              background: metrics.charging ? '#00ff88' : '#ffb800',
              boxShadow: `0 0 6px ${metrics.charging ? '#00ff88' : '#ffb800'}`,
            }}
          />
          {/* Charge segments */}
          {[25, 50, 75].map(p => (
            <div key={p} className="absolute top-0 bottom-0 w-px bg-hud-panel/50" style={{ left: `${p}%` }} />
          ))}
        </div>
      </div>

      {/* Security section */}
      <div>
        <button
          onClick={() => toggleSection('security')}
          className="w-full flex items-center justify-between mb-1.5"
        >
          <span className="font-orbitron text-[8px] tracking-widest text-hud-cyan/60">◈ SECURITY</span>
          <span className="font-mono-tech text-[8px] text-hud-cyan/40">{expandedSections.security ? '▼' : '▶'}</span>
        </button>
        {expandedSections.security && (
          <div className="flex flex-col gap-1.5">
            {/* Threat level */}
            <div className="p-2 rounded border transition-all duration-500"
              style={{ borderColor: `${threatColor}40`, background: `${threatColor}08` }}>
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-1.5">
                  <AlertTriangle size={11} style={{ color: threatColor }} />
                  <span className="font-orbitron text-[9px] text-hud-cyan/70">THREAT LEVEL</span>
                </div>
                <span className="font-orbitron text-[10px] font-bold" style={{ color: threatColor }}>
                  {metrics.threatLevel.toUpperCase()}
                </span>
              </div>
              {/* Animated scan line */}
              <div className="relative h-6 bg-black/30 rounded overflow-hidden">
                <div className="absolute inset-x-0 h-0.5 animate-scan-line"
                  style={{ background: `linear-gradient(90deg, transparent, ${threatColor}, transparent)` }} />
                <div className="absolute inset-0 flex items-center justify-center">
                  <span className="font-mono-tech text-[8px]" style={{ color: threatColor }}>
                    {metrics.threatLevel === 'low' ? '● NO ACTIVE THREATS' :
                      metrics.threatLevel === 'medium' ? '▲ MONITORING...' : '■ ALERT ACTIVE'}
                  </span>
                </div>
              </div>
            </div>

            {/* Firewall */}
            <div className="flex items-center justify-between p-1.5 rounded border border-hud-cyan/15">
              <div className="flex items-center gap-1.5">
                <Shield size={11} className="text-hud-green" />
                <span className="font-orbitron text-[9px] text-hud-cyan/70">FIREWALL</span>
              </div>
              <span className="font-mono-tech text-[9px] text-hud-green neon-text-green">ACTIVE</span>
            </div>

            {/* Encryption */}
            <div className="flex items-center justify-between p-1.5 rounded border border-hud-cyan/15">
              <div className="flex items-center gap-1.5">
                <Lock size={11} className="text-hud-blue" />
                <span className="font-orbitron text-[9px] text-hud-cyan/70">ENCRYPTION</span>
              </div>
              <span className="font-mono-tech text-[9px] text-hud-blue">AES-256</span>
            </div>
          </div>
        )}
      </div>

      {/* Temperature */}
      <div>
        <button
          onClick={() => toggleSection('environment')}
          className="w-full flex items-center justify-between mb-1.5"
        >
          <span className="font-orbitron text-[8px] tracking-widest text-hud-cyan/60">◈ ENVIRONMENT</span>
          <span className="font-mono-tech text-[8px] text-hud-cyan/40">{expandedSections.environment ? '▼' : '▶'}</span>
        </button>
        {expandedSections.environment && (
          <div className="p-2 rounded border border-hud-cyan/15">
            <div className="flex items-center gap-3">
              <RadialGauge
                value={metrics.temperature}
                max={100}
                color={metrics.temperature > 80 ? '#ff3b3b' : metrics.temperature > 70 ? '#ffb800' : '#00f5ff'}
                size={52}
              />
              <div className="flex-1">
                <div className="flex items-center gap-1.5 mb-1">
                  <Thermometer size={11} className={
                    metrics.temperature > 80 ? 'text-hud-red' :
                      metrics.temperature > 70 ? 'text-hud-amber' : 'text-hud-cyan'
                  } />
                  <span className="font-orbitron text-[9px] text-hud-cyan/70">CORE TEMP</span>
                </div>
                <div className="font-orbitron text-base font-bold" style={{
                  color: metrics.temperature > 80 ? '#ff3b3b' : metrics.temperature > 70 ? '#ffb800' : '#00f5ff'
                }}>
                  {Math.round(metrics.temperature)}°C
                </div>
                <div className="font-mono-tech text-[8px] text-hud-cyan/40 mt-0.5">
                  STATUS: {metrics.temperature > 80 ? 'CRITICAL' : metrics.temperature > 70 ? 'WARNING' : 'NOMINAL'}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Sandbox Telemetry */}
      <div>
        <button
          onClick={() => toggleSection('sandbox')}
          className="w-full flex items-center justify-between mb-1.5"
        >
          <span className="font-orbitron text-[8px] tracking-widest text-hud-cyan/60">◈ EXECUTION SANDBOX</span>
          <span className="font-mono-tech text-[8px] text-hud-cyan/40">{expandedSections.sandbox ? '▼' : '▶'}</span>
        </button>
        {expandedSections.sandbox && (
          <div className="flex flex-col gap-1.5 p-2 rounded border border-hud-cyan/15 bg-hud-cyan/5">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 font-orbitron text-[9px] text-hud-cyan/70">
                <Terminal size={11} className={sandbox_state.is_running ? "text-hud-green" : "text-hud-red"} />
                CONTAINER
              </span>
              <span className={`font-mono-tech text-[9px] ${sandbox_state.is_running ? "text-hud-green neon-text-green" : "text-hud-red"}`}>
                {sandbox_state.is_running ? 'ONLINE' : 'OFFLINE'}
              </span>
            </div>
            {sandbox_state.is_running && (
              <div className="mt-1">
                <div className="font-orbitron text-[8px] text-hud-cyan/50 mb-0.5 flex justify-between">
                  <span>LAST COMMAND</span>
                  {sandbox_state.cmd_active && <span className="text-hud-amber animate-pulse">EXECUTING...</span>}
                </div>
                <div className={`p-1.5 bg-black/50 border rounded font-mono-tech text-[8px] truncate ${sandbox_state.cmd_active ? 'border-hud-amber/30 text-hud-amber' : 'border-hud-cyan/20 text-hud-cyan/70'}`}>
                  $ {sandbox_state.last_cmd}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

    </div>
  );
}
