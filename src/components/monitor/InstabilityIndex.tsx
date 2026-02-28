/**
 * InstabilityIndex — Right floating panel.
 * Ranks countries by instability score.
 * When real data is loaded (GDELT + USGS), scores are computed from
 * event density in a ±5° bbox around each country's centroid.
 * Falls back to curated mock scores while data loads.
 */
import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { BarChart3 } from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { countries as mockCountries } from '@/data/mockData';
import type { CountryRisk } from '@/data/mockData';
import type { RealEvent } from '@/store/useMonitorStore';
import { BasePanel } from './BasePanel';
import { Sparkline } from './Sparkline';
import { ScrollArea } from '@/components/ui/scroll-area';

const riskTextColor = (score: number) => {
  if (score >= 80) return 'text-neon-crimson';
  if (score >= 60) return 'text-neon-amber';
  if (score >= 40) return 'text-accent';
  return 'text-neon-green';
};

const riskBgColor = (score: number) => {
  if (score >= 80) return 'bg-destructive/20';
  if (score >= 60) return 'bg-accent/20';
  if (score >= 40) return 'bg-accent/10';
  return 'bg-neon-green/10';
};

const sparklineStroke = (score: number) => {
  if (score >= 80) return 'hsl(0, 85%, 55%)';
  if (score >= 60) return 'hsl(42, 95%, 55%)';
  if (score >= 40) return 'hsl(42, 95%, 45%)';
  return 'hsl(145, 80%, 45%)';
};

const SEVERITY_WEIGHT: Record<string, number> = {
  critical: 20,
  high: 10,
  medium: 5,
  low: 2,
};

/** 
 * For each mock country, count real events that fall within ±8° and add weighted score. 
 * Max possible boost = 40 points. Cap at 99.
 */
function computeRealRisk(country: CountryRisk, events: RealEvent[]): number {
  const RADIUS = 8;
  let boost = 0;
  for (const ev of events) {
    if (ev.lat === 0 && ev.lng === 0) continue;
    if (
      Math.abs(ev.lat - country.lat) < RADIUS &&
      Math.abs(ev.lng - country.lng) < RADIUS
    ) {
      boost += SEVERITY_WEIGHT[ev.severity] ?? 2;
    }
  }
  return Math.min(99, country.riskScore + Math.round(boost * 0.5));
}

export const InstabilityIndex = ({ accentColor = 'hsl(42 95% 55%)' }: { accentColor?: string }) => {
  const flyTo = useMonitorStore((s) => s.flyTo);
  const realWorldEvents = useMonitorStore((s) => s.realWorldEvents);
  const realEvents = useMonitorStore((s) => s.realEvents);
  const lastFetch = useMonitorStore((s) => s.lastFetch);

  const allRealEvents = useMemo(
    () => [...realWorldEvents, ...realEvents],
    [realWorldEvents, realEvents],
  );

  const sorted = useMemo(() => {
    const base = [...mockCountries];
    if (lastFetch === 0 || allRealEvents.length === 0) {
      return base.sort((a, b) => b.riskScore - a.riskScore);
    }
    return base
      .map((c) => ({ ...c, riskScore: computeRealRisk(c, allRealEvents) }))
      .sort((a, b) => b.riskScore - a.riskScore);
  }, [allRealEvents, lastFetch]);

  const isLive = lastFetch > 0 && allRealEvents.length > 0;

  return (
    <BasePanel
      title="Instability Index"
      icon={<BarChart3 size={12} style={{ color: 'hsl(42 95% 55%)' }} />}
      badge={isLive ? <span className="text-[9px] font-mono animate-pulse" style={{ color: '#34d399' }}>⬤ LIVE</span> : undefined}
      accentColor="hsl(42 95% 55%)"
    >
      <ScrollArea className="max-h-[380px]">
        <div className="p-1.5 space-y-0.5">
          {sorted.map((country, i) => (
            <motion.button
              key={country.id}
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.025, type: 'spring', stiffness: 300, damping: 25 }}
              onClick={() => flyTo(country.lng, country.lat, 5)}
              className="w-full flex items-center gap-2 px-2 py-1.5 rounded-sm hover:bg-white/5 transition-all group text-left"
            >
              {/* Rank */}
              <span className="w-4 text-[9px] font-mono text-foreground/30 text-right shrink-0">{i + 1}</span>
              {/* Country name */}
              <span className="flex-1 text-[11px] font-medium text-foreground/80 group-hover:text-foreground transition-colors truncate">
                {country.name}
              </span>
              {/* Sparkline */}
              <Sparkline data={country.sparklineData} width={48} height={16} color={sparklineStroke(country.riskScore)} />
              {/* Risk score pill */}
              <div
                className={`px-1.5 py-0.5 rounded-sm text-[10px] font-mono font-bold w-7 text-center ${riskTextColor(country.riskScore)}`}
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: `1px solid currentColor`,
                  borderColor: `${riskTextColor(country.riskScore) === 'text-neon-crimson' ? 'hsl(0 90% 58% / 0.4)' : riskTextColor(country.riskScore) === 'text-neon-amber' ? 'hsl(42 95% 55% / 0.4)' : 'hsl(145 80% 50% / 0.4)'}`,
                }}
              >
                {country.riskScore}
              </div>
            </motion.button>
          ))}
        </div>
      </ScrollArea>
    </BasePanel>
  );
};
