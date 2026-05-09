import { useEffect, useState } from 'react';
import { ShieldAlert, ShieldCheck, ShieldX } from 'lucide-react';
import { apiGet } from '@/lib/api';

type SecurityStatus = {
  mode: string;
  recent_audit_count: number;
  blocked_count: number;
  recent_events: string[];
  policy?: {
    capabilities?: string[];
    allowlisted_actions?: string[];
    restricted_actions?: string[];
  };
};

export default function SecurityStatusPanel() {
  const [status, setStatus] = useState<SecurityStatus | null>(null);

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const data = await apiGet<SecurityStatus>('/api/security/status');
        if (!cancelled) setStatus(data);
      } catch {
        if (!cancelled) setStatus(null);
      }
    };

    load();
    const timer = window.setInterval(load, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const mode = status?.mode ?? 'assistant';
  const blocked = status?.blocked_count ?? 0;
  const recentEvents = status?.recent_events ?? [];
  const recent = recentEvents[recentEvents.length - 1] ?? 'monitoring';
  const Icon = blocked > 0 ? ShieldAlert : mode === 'locked' ? ShieldX : ShieldCheck;

  return (
    <div className="mx-1.5 mt-1.5 rounded border border-cyan-400/20 bg-black/35 backdrop-blur-md px-3 py-2 shadow-[0_0_24px_rgba(0,245,255,0.08)]">
      <div className="flex items-center gap-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-full border border-cyan-300/20 bg-cyan-400/10 text-cyan-200">
          <Icon size={16} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 text-[10px] uppercase tracking-[0.35em] text-cyan-100/80">
            <span>Security</span>
            <span className="text-cyan-300/50">•</span>
            <span>{mode}</span>
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px] text-cyan-50/70">
            <span>recent audit {status?.recent_audit_count ?? 0}</span>
            <span>blocked {blocked}</span>
            <span>last {recent.replace(/_/g, ' ')}</span>
          </div>
        </div>
        <div className="hidden sm:flex items-center gap-1 text-[9px] uppercase tracking-[0.3em] text-cyan-200/50">
          <span>policy</span>
          <span>{status?.policy?.capabilities?.slice(0, 2).join(' · ') ?? 'local gate'}</span>
        </div>
      </div>
    </div>
  );
}