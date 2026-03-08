/**
 * SENTINEL — unified threat intelligence + network security
 * Tabs: TACTICAL (TacticalModule) | NETWORK (SecurityModule)
 */
import { useState, useEffect } from 'react';
import { Shield, Eye, Fingerprint, Lock, AlertTriangle, Globe, RefreshCw, Search, Wifi, Activity, CheckCircle, XCircle } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api';
import { useSystemMetrics } from '@/hooks/useSystemMetrics';
import { useContextStore } from '@/store/useContextStore';

const API = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

/* ── shared helpers ──────────────────────────────────────────────────────── */
const riskColor = (level: string) => {
  switch (level?.toUpperCase()) {
    case 'CRITICAL': return '#ff2d55';
    case 'HIGH':     return '#ff9f0a';
    case 'MEDIUM':   return '#ffd60a';
    default:         return '#30d158';
  }
};
const trendIcon = (trend: string) =>
  (trend === 'ESCALATING' || trend === 'RISING') ? '↑' :
  (trend === 'DE-ESCALATING' || trend === 'FALLING') ? '↓' : '→';

/* ── Tactical types ──────────────────────────────────────────────────────── */
interface RegionRisk {
  id: string; risk_score: number; risk_level: string;
  dominant_threat: string; event_count: number; trend: string;
  hotspot: boolean; lat?: number; lng?: number;
}
interface ThreatSummary {
  global_risk_score: number; global_risk_level: string;
  total_events: number; hotspots: number; critical_count: number;
  top_threats?: Array<{ region: string; score: number; level: string; dominant_threat: string; trend: string }>;
}

/* ── Security types ──────────────────────────────────────────────────────── */
interface SecurityStatus {
  listening_ports: { port: number; process: string }[];
  connections: { total: number; established: number; external_hosts: string[] };
  threat_level: string;
  net_io: { bytes_sent_mb: number; bytes_recv_mb: number };
  top_processes: { name: string; cpu: number; mem: number; risk: string }[];
}

/* ── TACTICAL tab ────────────────────────────────────────────────────────── */
function TacticalTab() {
  const [blink, setBlink] = useState(false);
  useEffect(() => { const t = setInterval(() => setBlink(b => !b), 800); return () => clearInterval(t); }, []);

  const { data: summaryData, isLoading: summaryLoading } = useQuery<ThreatSummary>({
    queryKey: ['threat-summary'], queryFn: () => apiGet<ThreatSummary>('/api/threat/summary'),
    refetchInterval: 15000, retry: false,
  });
  const { data: regionsData, isLoading: regLoading, refetch } = useQuery<{ regions: RegionRisk[] }>({
    queryKey: ['threat-regions'], queryFn: () => apiGet<{ regions: RegionRisk[] }>('/api/threat/regions'),
    refetchInterval: 30000, retry: false,
  });

  const summary     = summaryData;
  const regions     = regionsData?.regions ?? [];
  const hotspots    = regions.filter(r => r.hotspot || r.risk_level === 'CRITICAL' || r.risk_level === 'HIGH');
  const globalLevel = summary?.global_risk_level ?? 'LOW';
  const isCritical  = globalLevel === 'CRITICAL';
  const isHigh      = globalLevel === 'HIGH';
  const alertColor  = isCritical ? '#ff2d55' : isHigh ? '#ff9f0a' : '#00f5ff';

  return (
    <div className="flex flex-col gap-3 p-3 h-full overflow-y-auto scrollbar-hud">
      <div className="flex items-center justify-between shrink-0">
        <span className="font-orbitron text-[9px]" style={{ color: alertColor }}>
          GLOBAL RISK — {globalLevel}
        </span>
        <button onClick={() => refetch()} className="p-1 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
          <RefreshCw size={10} className={regLoading || summaryLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      {summary && (
        <div className={`p-2 rounded border text-center transition-all duration-400 ${blink && isCritical ? 'bg-hud-red/20 border-hud-red/60' : 'bg-black/20 border-hud-cyan/20'}`}>
          <div className="flex justify-center gap-4">
            {[
              { label: 'RISK SCORE', value: summary.global_risk_score?.toFixed(0) ?? '—', color: riskColor(globalLevel) },
              { label: 'CRITICAL',   value: summary.critical_count ?? 0,                   color: '#ff2d55' },
              { label: 'HOTSPOTS',   value: summary.hotspots ?? 0,                         color: '#ff9f0a' },
              { label: 'EVENTS',     value: summary.total_events ?? 0,                     color: '#00f5ff' },
            ].map(s => (
              <div key={s.label} className="text-center">
                <div className="font-orbitron text-xl font-bold" style={{ color: s.color }}>{s.value}</div>
                <div className="font-orbitron text-[7px] text-hud-cyan/50">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="hud-panel rounded p-3">
        <div className="flex items-center gap-2 mb-2">
          <Globe size={11} className="text-hud-cyan" />
          <span className="font-orbitron text-[9px] text-hud-red/80">ACTIVE THREAT REGIONS</span>
        </div>
        {hotspots.length === 0 && !regLoading ? (
          <div className="text-center font-mono-tech text-[9px] text-hud-green/70 py-3 flex items-center justify-center gap-2">
            <Shield size={12} className="text-hud-green" /> All regions nominal
          </div>
        ) : (
          <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto scrollbar-hud">
            {hotspots.slice(0, 10).map(r => (
              <div key={r.id} className="flex items-center gap-2 p-1.5 rounded bg-black/30 border border-hud-cyan/10">
                <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: riskColor(r.risk_level), boxShadow: `0 0 4px ${riskColor(r.risk_level)}` }} />
                <span className="font-mono-tech text-[8px] text-hud-cyan/80 flex-1 truncate">{r.id.replace(/_/g, ' ')}</span>
                <span className="font-mono-tech text-[8px]" style={{ color: riskColor(r.risk_level) }}>{r.risk_level}</span>
                <span className="font-mono-tech text-[8px] text-hud-cyan/40">{trendIcon(r.trend)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {regions.length > 0 && (
        <div className="hud-panel rounded p-3">
          <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">SECTOR MAP</div>
          <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${Math.min(6, regions.length)}, 1fr)` }}>
            {regions.slice(0, 30).map(r => (
              <div key={r.id} title={`${r.id}: ${r.risk_level} (${r.risk_score?.toFixed(0)})`}
                className="h-6 rounded border border-hud-cyan/10 flex items-center justify-center cursor-pointer hover:scale-110 transition-transform"
                style={{ background: `${riskColor(r.risk_level)}${r.hotspot ? '50' : '20'}`, borderColor: r.hotspot ? riskColor(r.risk_level) : undefined }}>
                {r.hotspot && <span className="font-mono-tech text-[7px]" style={{ color: riskColor(r.risk_level) }}>!</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {!summary && !summaryLoading && (
        <div className="flex items-center gap-2 p-2 rounded border border-hud-amber/30 bg-hud-amber/5">
          <Shield size={12} className="text-hud-amber" />
          <span className="font-mono-tech text-[9px] text-hud-amber">THREAT INTEL OFFLINE</span>
        </div>
      )}
    </div>
  );
}

/* ── NETWORK tab ─────────────────────────────────────────────────────────── */
function NetworkTab() {
  const { auditMeta, threatLevel } = useSystemMetrics();
  const { setSelectedItem } = useContextStore();
  const [scanProgress, setScanProgress] = useState(0);
  const [scanLine, setScanLine] = useState(0);
  const [fingerProgress, setFingerProgress] = useState(0);
  const [biometricStatus, setBiometricStatus] = useState<'scanning' | 'verified' | 'denied'>('scanning');
  const [secStatus, setSecStatus] = useState<SecurityStatus | null>(null);

  useEffect(() => {
    const fetchSec = async () => {
      try {
        const r = await fetch(`${API}/api/security/status`);
        if (r.ok) setSecStatus(await r.json());
      } catch { /* silently skip */ }
    };
    fetchSec();
    const iv = setInterval(fetchSec, 15_000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setScanProgress(p => {
        if (p >= 100) { setBiometricStatus(Math.random() > 0.3 ? 'verified' : 'denied'); setTimeout(() => { setScanProgress(0); setBiometricStatus('scanning'); }, 3000); return 0; }
        return p + 1.5;
      });
      setScanLine(p => (p + 2) % 100);
      setFingerProgress(p => Math.min(100, p + 0.8));
    }, 50);
    return () => clearInterval(interval);
  }, []);

  const statusColor = biometricStatus === 'verified' ? '#00ff88' : biometricStatus === 'denied' ? '#ff3b3b' : '#00f5ff';
  const meta = auditMeta as Record<string, { count?: number; score?: number }> | null;

  return (
    <div className="flex flex-col gap-3 p-3 h-full overflow-y-auto scrollbar-hud">
      {/* Workspace Audit */}
      {meta && (
        <div className="hud-panel rounded p-3">
          <div className="flex items-center gap-2 mb-2">
            <Search size={11} className="text-hud-cyan" />
            <span className="font-orbitron text-[9px] text-hud-cyan/80">WORKSPACE AUDIT</span>
          </div>
          <div className="grid grid-cols-2 gap-2">
            {[
              { label: 'LINT', val: meta.flake8?.count, ok: !meta.flake8?.count },
              { label: 'TYPES', val: meta.mypy?.count, ok: !meta.mypy?.count },
              { label: 'SEC', val: meta.bandit?.count, ok: !meta.bandit?.count, critical: true },
              { label: 'COMPLEXITY', val: typeof meta.radon?.score === 'number' ? meta.radon.score.toFixed(2) : 'N/A', ok: true },
            ].map(e => (
              <div key={e.label} className="flex items-center justify-between bg-black/40 rounded p-1.5 border border-hud-cyan/10">
                <span className="text-[9px] text-hud-cyan/70">{e.label}</span>
                <span className={`text-[9px] ${!e.ok ? (e.critical ? 'text-hud-red animate-pulse' : 'text-hud-amber') : 'text-hud-green'}`}>
                  {typeof e.val === 'number' ? `${e.val} ISSUES` : e.val}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Live connections */}
      {secStatus && (
        <div className="hud-panel rounded p-3">
          <div className="flex items-center gap-2 mb-2">
            <Wifi size={11} className="text-hud-cyan" />
            <span className="font-orbitron text-[9px] text-hud-cyan/80">LIVE CONNECTIONS</span>
          </div>
          <div className="flex gap-3 mb-2">
            <div className="text-center">
              <div className="font-orbitron text-base font-bold text-hud-cyan">{secStatus.connections.total}</div>
              <div className="font-orbitron text-[7px] text-hud-cyan/50">TOTAL</div>
            </div>
            <div className="text-center">
              <div className="font-orbitron text-base font-bold text-hud-green">{secStatus.connections.established}</div>
              <div className="font-orbitron text-[7px] text-hud-cyan/50">ACTIVE</div>
            </div>
            <div className="text-center">
              <div className="font-orbitron text-base font-bold text-hud-amber">{secStatus.listening_ports.length}</div>
              <div className="font-orbitron text-[7px] text-hud-cyan/50">PORTS</div>
            </div>
          </div>
          <div className="flex flex-col gap-1 max-h-24 overflow-y-auto scrollbar-hud">
            {secStatus.listening_ports.slice(0, 8).map(p => (
              <div key={p.port} className="flex items-center justify-between bg-black/30 rounded p-1 border border-hud-cyan/10 cursor-pointer hover:border-hud-cyan/30"
                onClick={() => setSelectedItem({ module: 'security', type: 'port', label: `:${p.port} (${p.process})`, data: { port: p.port, process: p.process } })}>
                <span className="font-mono-tech text-[8px] text-hud-cyan/60">:{p.port}</span>
                <span className="font-mono-tech text-[8px] text-hud-cyan/40 truncate max-w-[120px]">{p.process}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top processes */}
      {secStatus?.top_processes && secStatus.top_processes.length > 0 && (
        <div className="hud-panel rounded p-3">
          <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">TOP PROCESSES</div>
          <div className="flex flex-col gap-1">
            {secStatus.top_processes.slice(0, 6).map(p => (
              <div key={p.name} className="flex items-center gap-2 p-1 rounded bg-black/30 border border-hud-cyan/10 cursor-pointer hover:border-hud-cyan/30"
                onClick={() => setSelectedItem({ module: 'security', type: 'process', label: p.name, data: p })}>
                <span className="font-mono-tech text-[8px] text-hud-cyan/80 flex-1 truncate">{p.name}</span>
                <span className={`font-mono-tech text-[8px] ${p.risk === 'high' ? 'text-hud-red' : p.risk === 'medium' ? 'text-hud-amber' : 'text-hud-green'}`}>
                  {p.risk?.toUpperCase()}
                </span>
                <span className="font-mono-tech text-[7px] text-hud-cyan/40">{p.cpu?.toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>
      )}

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
            <div key={e.label} className="text-center hud-panel rounded p-1.5">
              <div className="font-mono-tech text-[8px]" style={{ color: e.color }}>{e.status}</div>
              <div className="font-orbitron text-[7px] text-hud-cyan/50">{e.label}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Main export ─────────────────────────────────────────────────────────── */
type Tab = 'tactical' | 'network';

export default function SentinelModule() {
  const [tab, setTab] = useState<Tab>('tactical');
  const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: 'tactical', label: 'TACTICAL', icon: <AlertTriangle size={10} /> },
    { id: 'network',  label: 'NETWORK',  icon: <Shield size={10} /> },
  ];

  return (
    <div className="flex flex-col h-full">
      <div className="flex shrink-0 border-b border-hud-red/30">
        {TABS.map(t => (
          <button key={t.id} onClick={() => setTab(t.id)}
            className="flex-1 flex items-center justify-center gap-1.5 py-2 font-orbitron text-[9px] tracking-widest transition-colors"
            style={{
              color: tab === t.id ? '#ff9f0a' : 'rgba(255,255,255,0.3)',
              borderBottom: tab === t.id ? '2px solid #ff9f0a' : '2px solid transparent',
              background: tab === t.id ? 'rgba(255,159,10,0.05)' : 'transparent',
            }}>
            {t.icon}{t.label}
          </button>
        ))}
      </div>
      <div className="flex-1 min-h-0">
        {tab === 'tactical' && <TacticalTab />}
        {tab === 'network'  && <NetworkTab />}
      </div>
    </div>
  );
}
