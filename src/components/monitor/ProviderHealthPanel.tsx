/**
 * ProviderHealthPanel — SPARK Globe Intelligence API
 * Shows per-provider circuit-breaker status: ok / degraded / down / key_required
 * Fetches /api/globe/v1/getProviderHealth every 5 minutes.
 */
import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldAlert, ShieldX, KeyRound, RefreshCw } from 'lucide-react';
import { useMonitorStore, ProviderHealth } from '../../store/useMonitorStore';
import { BasePanel } from './BasePanel';

interface Props {
  accentColor?: string;
}

// ── Status config ────────────────────────────────────────────────────────────
const STATUS_CFG: Record<
  ProviderHealth['status'],
  { color: string; bg: string; Icon: typeof ShieldCheck; label: string }
> = {
  ok: {
    color: '#34d399',
    bg:    'rgba(52,211,153,0.12)',
    Icon:  ShieldCheck,
    label: 'OK',
  },
  degraded: {
    color: '#fbbf24',
    bg:    'rgba(251,191,36,0.12)',
    Icon:  ShieldAlert,
    label: 'DEGRADED',
  },
  down: {
    color: '#f87171',
    bg:    'rgba(248,113,113,0.14)',
    Icon:  ShieldX,
    label: 'DOWN',
  },
  key_required: {
    color: 'rgba(255,255,255,0.25)',
    bg:    'rgba(255,255,255,0.04)',
    Icon:  KeyRound,
    label: 'NO KEY',
  },
};

// Friendly display names for provider IDs
const PROVIDER_LABELS: Record<string, string> = {
  usgs:           'USGS Earthquakes',
  opensky:        'OpenSky Flights',
  eonet:          'NASA EONET',
  gdelt_conflict: 'GDELT Conflict',
  gdelt_intel:    'GDELT Intel',
  gdelt_news:     'GDELT News',
  coingecko:      'CoinGecko',
  frankfurter:    'Frankfurter FX',
  acled:          'ACLED Conflict',
  finnhub:        'Finnhub Stocks',
  eia:            'EIA Energy',
  nasa_firms:     'NASA FIRMS Fire',
  cloudflare:     'Cloudflare Radar',
};

export default function ProviderHealthPanel({ accentColor = '#00f5ff' }: Props) {
  const providerHealth        = useMonitorStore((s) => s.providerHealth);
  const providerHealthSummary = useMonitorStore((s) => s.providerHealthSummary);
  const fetchProviderHealth   = useMonitorStore((s) => s.fetchProviderHealth);

  // ── Fetch on mount + every 5 minutes ─────────────────────────────────────
  useEffect(() => {
    fetchProviderHealth();
    const t = setInterval(fetchProviderHealth, 5 * 60_000);
    return () => clearInterval(t);
  }, [fetchProviderHealth]);

  // ── Badge content for collapsed state ─────────────────────────────────────
  const badgeCount = providerHealthSummary
    ? (providerHealthSummary.degraded + providerHealthSummary.down)
    : 0;
  const badge =
    badgeCount > 0 ? (
      <span
        className="text-[9px] font-bold px-1.5 py-0.5 rounded-sm"
        style={{ background: badgeCount > 0 ? 'rgba(251,191,36,0.2)' : 'transparent',
                 color: '#fbbf24' }}
      >
        {badgeCount} ISSUE{badgeCount !== 1 ? 'S' : ''}
      </span>
    ) : null;

  // ── Group providers: first show non-key_required, then key_required ────────
  const active = providerHealth.filter((p) => p.status !== 'key_required');
  const keyed  = providerHealth.filter((p) => p.status === 'key_required');

  return (
    <BasePanel
      title="DATA PROVIDERS"
      accentColor={accentColor}
      defaultCollapsed={true}
      badge={badge}
      icon={
        <svg viewBox="0 0 16 16" fill="none" className="w-3 h-3">
          <circle cx="8" cy="8" r="6" stroke="currentColor" strokeWidth="1.5" />
          <path d="M5 8h6M8 5v6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      }
    >
      {/* ── Summary bar ─────────────────────────────────────────── */}
      {providerHealthSummary && (
        <div className="flex gap-2 mb-2 text-[9px] font-mono">
          <span style={{ color: '#34d399' }}>
            {providerHealthSummary.ok} OK
          </span>
          {providerHealthSummary.degraded > 0 && (
            <span style={{ color: '#fbbf24' }}>
              {providerHealthSummary.degraded} DEGRADED
            </span>
          )}
          {providerHealthSummary.down > 0 && (
            <span style={{ color: '#f87171' }}>
              {providerHealthSummary.down} DOWN
            </span>
          )}
          <span style={{ color: 'rgba(255,255,255,0.3)' }}>
            {providerHealthSummary.key_required} NO KEY
          </span>

          {/* Refresh button */}
          <button
            className="ml-auto opacity-50 hover:opacity-100 transition-opacity"
            onClick={fetchProviderHealth}
            title="Refresh provider health"
          >
            <RefreshCw size={9} />
          </button>
        </div>
      )}

      {/* ── No data yet ─────────────────────────────────────────── */}
      {providerHealth.length === 0 && (
        <p className="text-[10px] opacity-40 text-center py-3">
          Fetching provider status…
        </p>
      )}

      {/* ── Active providers ────────────────────────────────────── */}
      <div className="flex flex-col gap-1">
        {active.map((p) => (
          <ProviderRow key={p.name} provider={p} />
        ))}
      </div>

      {/* ── Key-required divider ─────────────────────────────────── */}
      {keyed.length > 0 && (
        <>
          <div className="flex items-center gap-2 my-2">
            <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.06)' }} />
            <span className="text-[8px] font-mono opacity-30 tracking-widest">OPTIONAL KEYS</span>
            <div className="flex-1 h-px" style={{ background: 'rgba(255,255,255,0.06)' }} />
          </div>
          <div className="flex flex-col gap-1">
            {keyed.map((p) => (
              <ProviderRow key={p.name} provider={p} />
            ))}
          </div>
        </>
      )}
    </BasePanel>
  );
}

// ── Individual provider row ──────────────────────────────────────────────────
function ProviderRow({ provider }: { provider: ProviderHealth }) {
  const cfg   = STATUS_CFG[provider.status];
  const label = PROVIDER_LABELS[provider.name] ?? provider.name;
  const Icon  = cfg.Icon;

  const isDown     = provider.status === 'down';
  const isDegraded = provider.status === 'degraded';

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="flex items-center gap-2 px-2 py-1 rounded"
      style={{ background: cfg.bg }}
      title={
        provider.lastError
          ? `${provider.lastError}${provider.cooldownRemaining ? ` — retry in ${provider.cooldownRemaining}s` : ''}`
          : undefined
      }
    >
      {/* Status dot */}
      <span className="shrink-0 relative">
        {(isDown || isDegraded) && (
          <span
            className="absolute inset-0 rounded-full animate-ping"
            style={{ background: cfg.color, opacity: 0.4 }}
          />
        )}
        <Icon size={10} style={{ color: cfg.color }} />
      </span>

      {/* Name */}
      <span
        className="text-[10px] font-mono flex-1 truncate"
        style={{ color: provider.status === 'key_required' ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.75)' }}
      >
        {label}
      </span>

      {/* Status label / cooldown */}
      <span className="text-[8px] font-mono shrink-0" style={{ color: cfg.color }}>
        {provider.cooldownRemaining > 0
          ? `${provider.cooldownRemaining}s`
          : provider.failureCount > 0 && provider.status !== 'down'
            ? `${provider.failureCount}✗`
            : cfg.label}
      </span>
    </motion.div>
  );
}
