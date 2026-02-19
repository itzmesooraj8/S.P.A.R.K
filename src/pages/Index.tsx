import { useEffect, useState } from 'react';
import { ThemeProvider, useHudTheme } from '@/contexts/ThemeContext';
import HudLayout from '@/components/hud/HudLayout';

function BootScreen() {
  const { setIsBooted } = useHudTheme();
  const [progress, setProgress] = useState(0);
  const [line, setLine] = useState(0);

  const bootLines = [
    'Initializing SPARK core systems...',
    'Loading neural network weights...',
    'Calibrating holographic display...',
    'Establishing secure channels...',
    'Synchronizing quantum databases...',
    'All systems nominal. SPARK online.',
  ];

  useEffect(() => {
    const prog = setInterval(() => setProgress(p => Math.min(100, p + 2)), 60);
    const ln = setInterval(() => setLine(l => Math.min(bootLines.length - 1, l + 1)), 500);
    const boot = setTimeout(() => setIsBooted(true), 3200);
    return () => { clearInterval(prog); clearInterval(ln); clearTimeout(boot); };
  }, [setIsBooted]);

  return (
    <div className="fixed inset-0 flex flex-col items-center justify-center z-[100]"
      style={{ background: 'radial-gradient(ellipse at center, #00022e 0%, #000814 60%, #000000 100%)' }}>
      {/* Logo */}
      <div className="mb-8 text-center">
        <div className="font-orbitron text-5xl font-black neon-text tracking-widest mb-2 animate-flicker">SPARK</div>
        <div className="font-mono-tech text-hud-cyan/50 text-sm tracking-widest">AI INTERFACE v4.1 — HOLOGRAPHIC HUD SYSTEM</div>
      </div>

      {/* Rotating rings */}
      <div className="relative w-32 h-32 mb-8">
        <svg width="128" height="128" viewBox="0 0 128 128" className="absolute inset-0">
          <circle cx="64" cy="64" r="58" fill="none" stroke="#00f5ff" strokeWidth="1" strokeDasharray="8 6" opacity="0.4" className="animate-rotate-cw-slow" style={{ transformOrigin: '64px 64px' }} />
          <circle cx="64" cy="64" r="45" fill="none" stroke="#00f5ff" strokeWidth="1.5" strokeDasharray="20 5" opacity="0.6" className="animate-rotate-ccw-med" style={{ transformOrigin: '64px 64px' }} />
          <circle cx="64" cy="64" r="30" fill="none" stroke="#00f5ff" strokeWidth="2" opacity="0.8" className="animate-rotate-cw-fast" style={{ transformOrigin: '64px 64px' }} />
          <circle cx="64" cy="64" r="10" fill="#00f5ff" opacity="0.2" />
          <circle cx="64" cy="64" r="5" fill="#00f5ff" style={{ filter: 'drop-shadow(0 0 8px #00f5ff)' }} />
        </svg>
      </div>

      {/* Boot log */}
      <div className="w-80 mb-6 bg-black/40 rounded border border-hud-cyan/20 p-3">
        {bootLines.slice(0, line + 1).map((l, i) => (
          <div key={i} className="font-mono-tech text-[10px] leading-5"
            style={{ color: i < line ? '#00f5ff80' : '#00f5ff' }}>
            {i < line ? '✓' : '▶'} {l}
          </div>
        ))}
      </div>

      {/* Progress bar */}
      <div className="w-80">
        <div className="flex justify-between mb-1">
          <span className="font-orbitron text-[9px] text-hud-cyan/60">BOOT SEQUENCE</span>
          <span className="font-orbitron text-[9px] text-hud-cyan">{progress}%</span>
        </div>
        <div className="h-1.5 rounded-full bg-black/40 overflow-hidden">
          <div className="h-full rounded-full transition-all duration-100"
            style={{ width: `${progress}%`, background: 'linear-gradient(90deg, #0066ff, #00f5ff)', boxShadow: '0 0 8px #00f5ff' }} />
        </div>
      </div>
    </div>
  );
}

function App() {
  const { isBooted } = useHudTheme();
  return isBooted ? <HudLayout /> : <BootScreen />;
}

export default function Index() {
  return (
    <ThemeProvider>
      <App />
    </ThemeProvider>
  );
}
