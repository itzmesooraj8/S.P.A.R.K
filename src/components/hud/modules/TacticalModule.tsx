import { useState, useEffect } from 'react';
import { AlertTriangle, Shield, Globe, RefreshCw } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiGet } from '@/lib/api';

interface RegionRisk {
  id: string;
  risk_score: number;
  risk_level: string;
  dominant_threat: string;
  event_count: number;
  trend: string;
  hotspot: boolean;
  lat?: number;
  lng?: number;
}

interface ThreatSummary {
  global_risk_score: number;
  global_risk_level: string;
  total_events: number;
  hotspots: number;
  critical_count: number;
  top_threats?: Array<{ region: string; score: number; level: string; dominant_threat: string; trend: string }>;
}

const riskColor = (level: string) => {
  switch (level?.toUpperCase()) {
    case 'CRITICAL': return '#ff2d55';
    case 'HIGH':     return '#ff9f0a';
    case 'MEDIUM':   return '#ffd60a';
    default:         return '#30d158';
  }
};

const trendIcon = (trend: string) => {
  if (trend === 'ESCALATING' || trend === 'RISING')  return '↑';
  if (trend === 'DE-ESCALATING' || trend === 'FALLING') return '↓';
  return '→';
};

export default function TacticalModule() {
  const [blink, setBlink] = useState(false);

  useEffect(() => {
    const t = setInterval(() => setBlink(b => !b), 800);
    return () => clearInterval(t);
  }, []);

  const { data: summaryData, isLoading: summaryLoading } = useQuery<ThreatSummary>({
    queryKey: ['threat-summary'],
    queryFn: () => apiGet<ThreatSummary>('/api/threat/summary'),
    refetchInterval: 15000,
    retry: false,
  });

  const { data: regionsData, isLoading: regLoading, refetch } = useQuery<{ regions: RegionRisk[] }>({
    queryKey: ['threat-regions'],
    queryFn: () => apiGet<{ regions: RegionRisk[] }>('/api/threat/regions'),
    refetchInterval: 30000,
    retry: false,
  });

  const summary    = summaryData;
  const regions    = regionsData?.regions ?? [];
  const hotspots   = regions.filter(r => r.hotspot || r.risk_level === 'CRITICAL' || r.risk_level === 'HIGH');
  const globalLevel = summary?.global_risk_level ?? 'LOW';
  const isCritical  = globalLevel === 'CRITICAL';
  const isHigh      = globalLevel === 'HIGH';
  const alertColor  = isCritical ? '#ff2d55' : isHigh ? '#ff9f0a' : '#00f5ff';

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto scrollbar-hud"
      style={{ borderColor: isCritical && blink ? 'rgba(255,45,85,0.5)' : 'transparent', transition: 'border-color 0.4s' }}>

      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-hud-red/40">
        <div className="flex items-center gap-2">
          <AlertTriangle size={14} style={{ color: alertColor }} className={isCritical ? 'animate-pulse' : ''} />
          <span className="font-orbitron text-xs tracking-widest" style={{ color: alertColor, textShadow: `0 0 10px ${alertColor}` }}>
            TACTICAL OVERLAY — {globalLevel}
          </span>
        </div>
        <button onClick={() => refetch()} className="p-1 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
          <RefreshCw size={10} className={regLoading || summaryLoading ? 'animate-spin' : ''} />
        </button>
      </div>

      {/* Global stats */}
      {summary && (
        <div className={`p-2 rounded border text-center transition-all duration-400 ${blink && isCritical ? 'bg-hud-red/20 border-hud-red/60' : 'bg-black/20 border-hud-cyan/20'}`}>
          <div className="flex justify-center gap-6">
            <div className="text-center">
              <div className="font-orbitron text-2xl font-bold" style={{ color: riskColor(globalLevel) }}>
                {summary.global_risk_score?.toFixed(0) ?? '—'}
              </div>
              <div className="font-orbitron text-[7px] text-hud-cyan/50">RISK SCORE</div>
            </div>
            <div className="text-center">
              <div className="font-orbitron text-2xl font-bold text-hud-red">{summary.critical_count ?? 0}</div>
              <div className="font-orbitron text-[7px] text-hud-cyan/50">CRITICAL</div>
            </div>
            <div className="text-center">
              <div className="font-orbitron text-2xl font-bold text-hud-amber">{summary.hotspots ?? 0}</div>
              <div className="font-orbitron text-[7px] text-hud-cyan/50">HOTSPOTS</div>
            </div>
            <div className="text-center">
              <div className="font-orbitron text-2xl font-bold text-hud-cyan">{summary.total_events ?? 0}</div>
              <div className="font-orbitron text-[7px] text-hud-cyan/50">EVENTS</div>
            </div>
          </div>
        </div>
      )}

      {/* THREAT REGIONS */}
      <div className="hud-panel rounded p-3">
        <div className="flex items-center gap-2 mb-2">
          <Globe size={11} className="text-hud-cyan" />
          <div className="font-orbitron text-[9px] text-hud-red/80">ACTIVE THREAT REGIONS</div>
        </div>

        {hotspots.length === 0 && !regLoading ? (
          <div className="text-center font-mono-tech text-[9px] text-hud-green/70 py-3 flex items-center justify-center gap-2">
            <Shield size={12} className="text-hud-green" />
            All regions nominal — no active hotspots
          </div>
        ) : (
          <div className="flex flex-col gap-1.5 max-h-48 overflow-y-auto scrollbar-hud">
            {hotspots.slice(0, 10).map((r) => (
              <div key={r.id} className="flex items-center gap-2 p-1.5 rounded bg-black/30 border border-hud-cyan/10">
                <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: riskColor(r.risk_level), boxShadow: `0 0 4px ${riskColor(r.risk_level)}` }} />
                <span className="font-mono-tech text-[8px] text-hud-cyan/80 flex-1 truncate">{r.id.replace(/_/g, ' ')}</span>
                <span className="font-mono-tech text-[8px]" style={{ color: riskColor(r.risk_level) }}>{r.risk_level}</span>
                <span className="font-mono-tech text-[8px] text-hud-cyan/40">{trendIcon(r.trend)}</span>
                <span className="font-mono-tech text-[8px] text-hud-cyan/50">{r.dominant_threat}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* All region grid (mini) */}
      {regions.length > 0 && (
        <div className="hud-panel rounded p-3">
          <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">SECTOR MAP</div>
          <div className="grid gap-1" style={{ gridTemplateColumns: `repeat(${Math.min(6, regions.length)}, 1fr)` }}>
            {regions.slice(0, 30).map(r => (
              <div
                key={r.id}
                title={`${r.id}: ${r.risk_level} (${r.risk_score?.toFixed(0)})`}
                className="h-6 rounded border border-hud-cyan/10 flex items-center justify-center cursor-pointer hover:scale-110 transition-transform"
                style={{
                  background: `${riskColor(r.risk_level)}${r.hotspot ? '50' : '20'}`,
                  borderColor: r.hotspot ? riskColor(r.risk_level) : undefined,
                }}
              >
                {r.hotspot && <span className="font-mono-tech text-[7px]" style={{ color: riskColor(r.risk_level) }}>!</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* No backend fallback */}
      {!summary && !summaryLoading && (
        <div className="flex items-center gap-2 p-2 rounded border border-hud-amber/30 bg-hud-amber/5">
          <Shield size={12} className="text-hud-amber" />
          <span className="font-mono-tech text-[9px] text-hud-amber">THREAT INTEL OFFLINE — Backend not connected</span>
        </div>
      )}

      <div className="flex items-center gap-2 p-2 rounded border border-hud-cyan/20 bg-black/20 mt-auto">
        <Shield size={12} className="text-hud-cyan" />
        <span className="font-mono-tech text-[9px] text-hud-cyan/60">DEFENSIVE PROTOCOLS ACTIVE | SPARK THREAT ENGINE v3.0</span>
      </div>
    </div>
  );
}
