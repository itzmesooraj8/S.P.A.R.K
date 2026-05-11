import { useState, useEffect } from 'react';
import { Satellite, Cpu } from 'lucide-react';

const SATELLITES = [
  { name: 'NEX-01', lat: 45, lon: 120, alt: 408 },
  { name: 'NEX-02', lat: -30, lon: -60, alt: 520 },
  { name: 'NEX-03', lat: 10, lon: 30, alt: 380 },
  { name: 'NEX-04', lat: 60, lon: 200, alt: 612 },
];

export default function SatelliteModule() {
  const [angle, setAngle] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setAngle(a => (a + 0.5) % 360), 50);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto scrollbar-hud">
      <div className="flex items-center gap-2 pb-2 border-b border-hud-cyan/20">
        <Satellite size={14} className="text-hud-cyan" />
        <span className="font-orbitron text-xs tracking-widest neon-text">SATELLITE TRACKER</span>
      </div>
      <div className="relative w-full aspect-square max-h-64 mx-auto">
        <svg width="100%" height="100%" viewBox="0 0 260 260">
          {/* Earth */}
          <circle cx="130" cy="130" r="30" fill="#001a33" stroke="#00f5ff" strokeWidth="1.5" strokeOpacity="0.6" />
          <circle cx="130" cy="130" r="30" fill="none" stroke="#00f5ff" strokeWidth="0.5" strokeOpacity="0.3"
            strokeDasharray="4 6" style={{ animation: 'rotate-cw 20s linear infinite', transformOrigin: '130px 130px' }} />
          {/* Orbits */}
          {[50, 70, 90, 110].map((r, i) => (
            <ellipse key={i} cx="130" cy="130" rx={r} ry={r * 0.4}
              fill="none" stroke="#00f5ff" strokeWidth="0.5" strokeOpacity="0.2"
              transform={`rotate(${i * 35} 130 130)`} />
          ))}
          {/* Satellites */}
          {SATELLITES.map((sat, i) => {
            const r = 50 + i * 20;
            const a = ((angle + i * 90) * Math.PI) / 180;
            const x = 130 + Math.cos(a) * r;
            const y = 130 + Math.sin(a) * r * 0.4;
            return (
              <g key={sat.name}>
                <circle cx={x} cy={y} r="4" fill="#00f5ff" opacity="0.9"
                  style={{ filter: 'drop-shadow(0 0 4px #00f5ff)' }} />
                <line x1="130" y1="130" x2={x} y2={y} stroke="#00f5ff" strokeWidth="0.3" strokeOpacity="0.3" strokeDasharray="3 4" />
                <text x={x + 6} y={y + 3} fill="#00f5ff" fontSize="7" fontFamily="Orbitron" opacity="0.8">{sat.name}</text>
              </g>
            );
          })}
        </svg>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {SATELLITES.map(sat => (
          <div key={sat.name} className="hud-panel rounded p-2">
            <div className="flex items-center gap-1.5 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-hud-cyan animate-pulse" />
              <span className="font-orbitron text-[9px] text-hud-cyan">{sat.name}</span>
            </div>
            <div className="font-mono-tech text-[8px] text-hud-cyan/50">LAT: {sat.lat}°</div>
            <div className="font-mono-tech text-[8px] text-hud-cyan/50">LON: {sat.lon}°</div>
            <div className="font-mono-tech text-[8px] text-hud-amber">ALT: {sat.alt}km</div>
          </div>
        ))}
      </div>
    </div>
  );
}
