import { AreaChart, Area, BarChart, Bar, RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, XAxis, YAxis, Tooltip } from 'recharts';
import { useSystemMetrics } from '@/hooks/useSystemMetrics';
import { BarChart2 } from 'lucide-react';

const MOCK_WEEKLY = [
  { day: 'MON', cpu: 45, ram: 62, net: 30 },
  { day: 'TUE', cpu: 78, ram: 71, net: 55 },
  { day: 'WED', cpu: 52, ram: 68, net: 42 },
  { day: 'THU', cpu: 89, ram: 75, net: 78 },
  { day: 'FRI', cpu: 63, ram: 69, net: 61 },
  { day: 'SAT', cpu: 34, ram: 55, net: 25 },
  { day: 'SUN', cpu: 41, ram: 58, net: 33 },
];

const RADAR_DATA = [
  { subject: 'CPU', A: 72 }, { subject: 'RAM', A: 68 },
  { subject: 'GPU', A: 55 }, { subject: 'NET', A: 83 },
  { subject: 'DISK', A: 45 }, { subject: 'TEMP', A: 62 },
];

export default function AnalyticsModule({ metrics }: { metrics: ReturnType<typeof useSystemMetrics> }) {
  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto scrollbar-hud">
      <div className="flex items-center gap-2 pb-2 border-b border-hud-cyan/20">
        <BarChart2 size={14} className="text-hud-cyan" />
        <span className="font-orbitron text-xs tracking-widest neon-text">ANALYTICS DASHBOARD</span>
      </div>

      {/* Real-time area chart */}
      <div className="hud-panel rounded p-3">
        <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">REAL-TIME PERFORMANCE</div>
        <ResponsiveContainer width="100%" height={100}>
          <AreaChart data={metrics.cpuHistory}>
            <defs>
              <linearGradient id="cpuGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#00f5ff" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#00f5ff" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="ramGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#0066ff" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#0066ff" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis dataKey="time" hide />
            <YAxis domain={[0, 100]} hide />
            <Tooltip
              contentStyle={{ background: '#00050f', border: '1px solid #00f5ff33', fontSize: '10px', fontFamily: 'Orbitron' }}
              labelStyle={{ color: '#00f5ff' }}
            />
            <Area type="monotone" dataKey="value" stroke="#00f5ff" strokeWidth={2} fill="url(#cpuGrad)" dot={false} name="CPU" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Weekly bar chart */}
      <div className="hud-panel rounded p-3">
        <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">WEEKLY LOAD ANALYSIS</div>
        <ResponsiveContainer width="100%" height={100}>
          <BarChart data={MOCK_WEEKLY} barCategoryGap="30%">
            <XAxis dataKey="day" tick={{ fill: '#00f5ff', fontSize: 8, fontFamily: 'Orbitron' }} axisLine={false} tickLine={false} />
            <YAxis hide domain={[0, 100]} />
            <Tooltip
              contentStyle={{ background: '#00050f', border: '1px solid #00f5ff33', fontSize: '10px', fontFamily: 'Orbitron' }}
            />
            <Bar dataKey="cpu" fill="#00f5ff" fillOpacity={0.7} radius={[2, 2, 0, 0]} name="CPU" />
            <Bar dataKey="ram" fill="#0066ff" fillOpacity={0.7} radius={[2, 2, 0, 0]} name="RAM" />
            <Bar dataKey="net" fill="#00ff88" fillOpacity={0.7} radius={[2, 2, 0, 0]} name="NET" />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Radar chart */}
      <div className="hud-panel rounded p-3">
        <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">SYSTEM PROFILE RADAR</div>
        <ResponsiveContainer width="100%" height={150}>
          <RadarChart data={RADAR_DATA}>
            <PolarGrid stroke="#00f5ff" strokeOpacity={0.2} />
            <PolarAngleAxis dataKey="subject" tick={{ fill: '#00f5ff', fontSize: 9, fontFamily: 'Orbitron' }} />
            <Radar dataKey="A" stroke="#00f5ff" fill="#00f5ff" fillOpacity={0.2} strokeWidth={2} />
          </RadarChart>
        </ResponsiveContainer>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-3 gap-2">
        {[
          { label: 'UPTIME', value: '99.97%', color: '#00ff88' },
          { label: 'REQUESTS', value: '2.4K/s', color: '#00f5ff' },
          { label: 'LATENCY', value: `${metrics.ping}ms`, color: '#0066ff' },
          { label: 'CPU AVG', value: `${Math.round(metrics.cpu)}%`, color: '#00f5ff' },
          { label: 'RAM USED', value: `${Math.round(metrics.ram)}%`, color: '#0066ff' },
          { label: 'THREADS', value: metrics.processes.toString(), color: '#8b00ff' },
        ].map(s => (
          <div key={s.label} className="hud-panel rounded p-2 text-center">
            <div className="font-orbitron text-base font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="font-orbitron text-[7px] text-hud-cyan/50 mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
