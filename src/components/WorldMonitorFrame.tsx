import React, { useState, useCallback } from 'react';

// WorldMonitor runs as a fully independent Vite dev server on port 3000.
// Embedding via iframe gives it a completely isolated DOM, CSS, and JS env —
// no CSS conflicts, no sizing issues, no library mounting problems.
const WM_ORIGIN = (import.meta as any).env?.VITE_WM_URL ?? 'http://localhost:3000';

interface WorldMonitorFrameProps {
  // variant is kept for API compatibility but WM's own tab UI handles switching
  variant?: string;
}

const WorldMonitorFrame: React.FC<WorldMonitorFrameProps> = () => {
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');

  const handleLoad = useCallback(() => setStatus('ready'), []);
  const handleError = useCallback(() => setStatus('error'), []);

  return (
    <div className="relative w-full h-full bg-black">
      {/* Loading overlay */}
      {status === 'loading' && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-black/90">
          <div className="w-8 h-8 border-2 border-hud-cyan/30 border-t-hud-cyan rounded-full animate-spin" />
          <span className="font-orbitron text-[10px] neon-text tracking-widest animate-pulse">LOADING WORLD MONITOR…</span>
        </div>
      )}

      {/* Error overlay */}
      {status === 'error' && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-3 bg-black/90">
          <span className="text-3xl">📡</span>
          <span className="font-orbitron text-[11px] neon-text-red tracking-widest">WORLD MONITOR OFFLINE</span>
          <span className="font-mono text-[9px] text-hud-cyan/40 text-center max-w-xs">
            WorldMonitor dev server not reachable on {WM_ORIGIN}.<br />
            It starts automatically with <code className="text-hud-cyan/70">npm run dev</code>.
          </span>
        </div>
      )}

      <iframe
        src={WM_ORIGIN}
        title="SPARK World Monitor"
        className="w-full h-full border-0"
        style={{ display: status === 'error' ? 'none' : 'block' }}
        onLoad={handleLoad}
        onError={handleError}
        allow="geolocation"
        // allow WM to access its own APIs normally
        sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-popups-to-escape-sandbox"
      />
    </div>
  );
};

export default WorldMonitorFrame;
