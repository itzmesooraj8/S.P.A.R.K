import { useState, useEffect } from 'react';
import { AlertTriangle, Shield } from 'lucide-react';

export default function TacticalModule() {
  const [blink, setBlink] = useState(false);
  const [threatZones] = useState(() =>
    Array.from({ length: 25 }, (_, i) => ({
      id: i, threat: Math.random() > 0.75,
      level: Math.random() > 0.9 ? 'critical' : Math.random() > 0.7 ? 'high' : 'normal',
    }))
  );

  useEffect(() => {
    const t = setInterval(() => setBlink(b => !b), 800);
    return () => clearInterval(t);
  }, []);

  const cellColor = (z: typeof threatZones[0]) => {
    if (z.level === 'critical') return blink ? 'rgba(255,59,59,0.6)' : 'rgba(255,59,59,0.2)';
    if (z.level === 'high') return 'rgba(255,184,0,0.3)';
    if (z.threat) return 'rgba(0,245,255,0.1)';
    return 'rgba(0,245,255,0.04)';
  };

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto scrollbar-hud"
      style={{ borderColor: blink ? 'rgba(255,59,59,0.5)' : 'transparent', transition: 'border-color 0.4s' }}>
      <div className="flex items-center gap-2 pb-2 border-b border-hud-red/40">
        <AlertTriangle size={14} className="text-hud-red animate-pulse" />
        <span className="font-orbitron text-xs tracking-widest text-hud-red" style={{ textShadow: '0 0 10px #ff3b3b' }}>
          TACTICAL OVERLAY — RED ALERT
        </span>
      </div>
      {/* Alert banner */}
      <div className={`p-2 rounded border border-hud-red/60 text-center transition-all duration-400 ${blink ? 'bg-hud-red/20' : 'bg-hud-red/5'}`}>
        <span className="font-orbitron text-xs text-hud-red tracking-widest">⚠ COMBAT MODE ACTIVE ⚠</span>
      </div>
      {/* Threat map grid */}
      <div className="hud-panel rounded p-3">
        <div className="font-orbitron text-[9px] text-hud-red/60 mb-2">SECTOR THREAT MAP</div>
        <div className="grid gap-1" style={{ gridTemplateColumns: 'repeat(5, 1fr)' }}>
          {threatZones.map(z => (
            <div key={z.id} className="h-8 rounded border border-hud-red/20 flex items-center justify-center transition-all duration-400"
              style={{ background: cellColor(z) }}>
              {z.level === 'critical' && <span className="font-mono-tech text-[8px] text-hud-red">!</span>}
            </div>
          ))}
        </div>
      </div>
      {/* Status */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: 'CRITICAL ZONES', value: threatZones.filter(z => z.level === 'critical').length, color: '#ff3b3b' },
          { label: 'HIGH RISK', value: threatZones.filter(z => z.level === 'high').length, color: '#ffb800' },
          { label: 'MONITORED', value: threatZones.filter(z => z.threat).length, color: '#00f5ff' },
          { label: 'CLEAR', value: threatZones.filter(z => !z.threat).length, color: '#00ff88' },
        ].map(s => (
          <div key={s.label} className="hud-panel rounded p-2 text-center">
            <div className="font-orbitron text-lg font-bold" style={{ color: s.color }}>{s.value}</div>
            <div className="font-orbitron text-[7px] text-hud-cyan/50">{s.label}</div>
          </div>
        ))}
      </div>
      <div className="flex items-center gap-2 p-2 rounded border border-hud-red/30 bg-hud-red/5">
        <Shield size={12} className="text-hud-red" />
        <span className="font-mono-tech text-[9px] text-hud-red">DEFENSIVE PROTOCOLS ENGAGED — STANDBY</span>
      </div>
    </div>
  );
}
