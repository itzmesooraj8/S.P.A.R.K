import { useState, useEffect, useRef } from 'react';
import { Shield, Eye, Fingerprint, Lock, AlertTriangle, CheckCircle, XCircle, Search } from 'lucide-react';
import { useSystemMetrics } from '@/hooks/useSystemMetrics';

export default function SecurityModule() {
  const { auditMeta, threatLevel } = useSystemMetrics();
  const [scanProgress, setScanProgress] = useState(0);
  const [scanLine, setScanLine] = useState(0);
  const [fingerProgress, setFingerProgress] = useState(0);
  const [threatAlert, setThreatAlert] = useState(false);
  const [biometricStatus, setBiometricStatus] = useState<'scanning' | 'verified' | 'denied'>('scanning');

  useEffect(() => {
    const interval = setInterval(() => {
      setScanProgress(p => {
        if (p >= 100) {
          setBiometricStatus(Math.random() > 0.3 ? 'verified' : 'denied');
          setTimeout(() => { setScanProgress(0); setBiometricStatus('scanning'); }, 3000);
          return 0;
        }
        return p + 1.5;
      });
      setScanLine(p => (p + 2) % 100);
      setFingerProgress(p => Math.min(100, p + 0.8));
    }, 50);
    return () => clearInterval(interval);
  }, []);

  const statusColor = biometricStatus === 'verified' ? '#00ff88' : biometricStatus === 'denied' ? '#ff3b3b' : '#00f5ff';

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto scrollbar-hud">
      <div className="flex items-center gap-2 pb-2 border-b border-hud-cyan/20">
        <Shield size={14} className="text-hud-cyan" />
        <span className="font-orbitron text-xs tracking-widest neon-text">SECURITY MODULE</span>
      </div>

      {/* Code Audit Status (Real) */}
      <div className="hud-panel rounded p-3 mb-4">
        <div className="flex items-center justify-between mb-2">
           <div className="flex items-center gap-2">
             <Search size={11} className="text-hud-cyan" />
             <span className="font-orbitron text-[9px] text-hud-cyan/80">WORKSPACE AUDIT</span>
           </div>
           {auditMeta?.timestamp && (
             <span className="text-[9px] text-hud-cyan/40">
               {new Date(auditMeta.timestamp * 1000).toLocaleTimeString()}
             </span>
           )}
        </div>
        
        {!auditMeta ? (
          <div className="text-center font-mono-tech text-[10px] text-hud-cyan/40 py-2">
             Waiting for audit telemetry...
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-2">
             {/* Flake8 */}
             <div className="flex items-center justify-between bg-black/40 rounded p-1.5 border border-hud-cyan/10">
               <span className="text-[9px] text-hud-cyan/70">LINT (Flake8)</span>
               {auditMeta.flake8?.status === 'success' ? (
                 <span className={`text-[9px] ${auditMeta.flake8.count > 0 ? 'text-hud-amber' : 'text-hud-green'}`}>
                   {auditMeta.flake8.count} ISSUES
                 </span>
               ) : (
                 <span className="text-[9px] text-hud-red">FAILED</span>
               )}
             </div>

             {/* Mypy */}
             <div className="flex items-center justify-between bg-black/40 rounded p-1.5 border border-hud-cyan/10">
               <span className="text-[9px] text-hud-cyan/70">TYPES (Mypy)</span>
               {auditMeta.mypy?.status === 'success' ? (
                 <span className={`text-[9px] ${auditMeta.mypy.count > 0 ? 'text-hud-amber' : 'text-hud-green'}`}>
                   {auditMeta.mypy.count} ERRORS
                 </span>
               ) : (
                 <span className="text-[9px] text-hud-red">FAILED</span>
               )}
             </div>

             {/* Bandit */}
             <div className="flex items-center justify-between bg-black/40 rounded p-1.5 border border-hud-cyan/10">
               <span className="text-[9px] text-hud-cyan/70">SEC (Bandit)</span>
               {auditMeta.bandit?.status === 'success' ? (
                 <span className={`text-[9px] ${auditMeta.bandit.count > 0 ? 'text-hud-red animate-pulse' : 'text-hud-green'}`}>
                   {auditMeta.bandit.count} VULNS
                 </span>
               ) : (
                 <span className="text-[9px] text-hud-red">FAILED</span>
               )}
             </div>
             
             {/* Complexity */}
             <div className="flex items-center justify-between bg-black/40 rounded p-1.5 border border-hud-cyan/10">
               <span className="text-[9px] text-hud-cyan/70">COMPLEXITY</span>
               <span className="text-[9px] text-hud-cyan">
                 {typeof auditMeta.radon?.score === 'number' ? auditMeta.radon.score.toFixed(2) : 'N/A'}
               </span>
             </div>
          </div>
        )}
      </div>

      <div className="grid grid-cols-2 gap-4">
        {/* Biometric scan */}
        <div className="hud-panel rounded p-3">
          <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">BIOMETRIC SCAN</div>
          <div className="relative w-full h-32 bg-black/40 rounded border border-hud-cyan/20 overflow-hidden flex items-center justify-center">
            {/* Face silhouette SVG */}
            <svg width="60" height="80" viewBox="0 0 60 80" style={{ opacity: 0.4 }}>
              <ellipse cx="30" cy="35" rx="22" ry="28" fill="none" stroke="#00f5ff" strokeWidth="1.5" />
              <ellipse cx="22" cy="30" rx="3" ry="4" fill="#00f5ff" opacity={0.6} />
              <ellipse cx="38" cy="30" rx="3" ry="4" fill="#00f5ff" opacity={0.6} />
              <path d="M 20 48 Q 30 56 40 48" fill="none" stroke="#00f5ff" strokeWidth="1.5" />
              <line x1="30" y1="63" x2="30" y2="80" stroke="#00f5ff" strokeWidth="1" opacity={0.4} />
            </svg>
            {/* Grid overlay */}
            <div className="absolute inset-0 pointer-events-none"
              style={{ backgroundImage: 'linear-gradient(#00f5ff 1px, transparent 1px), linear-gradient(90deg, #00f5ff 1px, transparent 1px)', backgroundSize: '8px 8px', opacity: 0.06 }} />
            {/* Scan line */}
            <div className="absolute inset-x-0 h-0.5"
              style={{ top: `${scanLine}%`, background: 'linear-gradient(90deg, transparent, #00f5ff, transparent)', opacity: 0.8 }} />
            {/* Status */}
            <div className="absolute bottom-1 inset-x-0 text-center font-orbitron text-[8px]"
              style={{ color: statusColor }}>
              {biometricStatus.toUpperCase()}
            </div>
          </div>
          <div className="mt-1.5 h-1 rounded-full bg-black/40">
            <div className="h-full rounded-full transition-all"
              style={{ width: `${scanProgress}%`, background: statusColor }} />
          </div>
        </div>

        {/* Fingerprint */}
        <div className="hud-panel rounded p-3">
          <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">FINGERPRINT</div>
          <div className="relative w-full h-32 flex items-center justify-center">
            <svg width="80" height="100" viewBox="0 0 80 100">
              {[8, 14, 20, 26, 32, 38].map((r, i) => (
                <ellipse key={i} cx="40" cy="50" rx={r} ry={r * 1.2}
                  fill="none" stroke="#00f5ff" strokeWidth="1.5"
                  opacity={(fingerProgress / 100) * 0.8}
                  strokeDasharray={`${(fingerProgress / 100) * (2 * Math.PI * r)} ${2 * Math.PI * r}`}
                  style={{ filter: `drop-shadow(0 0 2px #00f5ff)` }}
                />
              ))}
              <circle cx="40" cy="50" r="3" fill="#00f5ff"
                opacity={fingerProgress > 50 ? 1 : 0}
                style={{ filter: 'drop-shadow(0 0 4px #00f5ff)' }} />
            </svg>
          </div>
          <div className="mt-1 text-center font-orbitron text-[8px] text-hud-cyan/60">
            {fingerProgress < 100 ? `${Math.round(fingerProgress)}% MAPPED` : 'VERIFIED'}
          </div>
        </div>
      </div>

      {/* Encryption status */}
      <div className="hud-panel rounded p-3">
        <div className="flex items-center gap-2 mb-2">
          <Lock size={11} className="text-hud-blue" />
          <span className="font-orbitron text-[9px] text-hud-cyan/60">ENCRYPTION STATUS</span>
        </div>
        <div className="grid grid-cols-3 gap-2">
          {[
            { label: 'AES-256', status: 'ACTIVE', color: '#00ff88' },
            { label: 'RSA-4096', status: 'ACTIVE', color: '#00ff88' },
            { label: 'QUANTUM', status: 'PENDING', color: '#ffb800' },
          ].map(e => (
            <div key={e.label} className="p-1.5 rounded border border-hud-cyan/15 text-center">
              <div className="font-orbitron text-[8px] text-hud-cyan/60">{e.label}</div>
              <div className="font-mono-tech text-[9px] mt-0.5" style={{ color: e.color }}>{e.status}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Threat map */}
      <div className="hud-panel rounded p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Eye size={11} className="text-hud-cyan" />
            <span className="font-orbitron text-[9px] text-hud-cyan/60">THREAT MAP</span>
          </div>
          <button
            onClick={() => setThreatAlert(v => !v)}
            className="font-orbitron text-[8px] px-2 py-0.5 rounded border border-hud-red/40 text-hud-red hover:bg-hud-red/10"
          >
            SIMULATE ALERT
          </button>
        </div>
        {threatAlert && (
          <div className="p-2 rounded border border-hud-red/60 bg-hud-red/10 flex items-center gap-2 animate-pulse">
            <AlertTriangle size={12} className="text-hud-red" />
            <span className="font-orbitron text-[9px] text-hud-red">⚠ THREAT DETECTED — SECTOR 7G</span>
          </div>
        )}
        <div className="grid grid-cols-4 gap-1 mt-2">
          {Array.from({ length: 16 }, (_, i) => (
            <div key={i} className="h-4 rounded-sm border border-hud-cyan/15"
              style={{ background: Math.random() > 0.85 ? 'rgba(255,59,59,0.4)' : Math.random() > 0.7 ? 'rgba(255,184,0,0.2)' : 'rgba(0,245,255,0.05)' }} />
          ))}
        </div>
      </div>
    </div>
  );
}
