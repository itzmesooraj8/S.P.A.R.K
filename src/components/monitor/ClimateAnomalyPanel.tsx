/**
 * ClimateAnomalyPanel — Shows NASA EONET open natural events.
 * Mirrors worldmonitor ClimateAnomalyPanel feature.
 * Categories: wildfires, severeStorms, volcanoes, floods, drought, etc.
 */
import { useMemo } from 'react';
import { motion } from 'framer-motion';
import { Flame, Wind, Mountain, Droplets, Cloud, Globe } from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { BasePanel } from './BasePanel';
import { ScrollArea } from '@/components/ui/scroll-area';
import type { RealEvent, Severity } from '@/store/useMonitorStore';

const categoryConfig: Record<
  string,
  { label: string; Icon: typeof Globe; color: string }
> = {
  wildfires:     { label: 'Wildfire',       Icon: Flame,    color: 'text-orange-400' },
  severeStorms:  { label: 'Severe Storm',   Icon: Wind,     color: 'text-blue-400' },
  volcanoes:     { label: 'Volcano',        Icon: Mountain, color: 'text-red-400' },
  floods:        { label: 'Flooding',       Icon: Droplets, color: 'text-cyan-400' },
  drought:       { label: 'Drought',        Icon: Cloud,    color: 'text-yellow-600' },
  dustHaze:      { label: 'Dust / Haze',    Icon: Wind,     color: 'text-yellow-400' },
  seaLakeIce:    { label: 'Sea Ice',        Icon: Globe,    color: 'text-sky-300' },
  earthquakes:   { label: 'Earthquake',     Icon: Globe,    color: 'text-neon-amber' },
  landslides:    { label: 'Landslide',      Icon: Mountain, color: 'text-amber-700' },
  tempExtremes:  { label: 'Temp Extreme',   Icon: Cloud,    color: 'text-red-300' },
};

const severityDot: Record<Severity, string> = {
  critical: 'bg-neon-crimson pulse-severity',
  high:     'bg-neon-amber',
  medium:   'bg-accent',
  low:      'bg-neon-green',
};

/** Format EONET iso date */
const fmtDate = (d: string) => {
  try {
    return new Date(d).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  } catch {
    return d?.slice(0, 10) || '';
  }
};

export const ClimateAnomalyPanel = ({ accentColor = 'hsl(210 100% 60%)' }: { accentColor?: string }) => {
  const realClimateEvents = useMonitorStore((s) => s.realClimateEvents);
  const realFireEvents = useMonitorStore((s) => s.realFireEvents);
  const flyTo = useMonitorStore((s) => s.flyTo);
  const lastFetch = useMonitorStore((s) => s.lastFetch);

  // Merge fires into climate events for unified display
  const allEvents = useMemo<RealEvent[]>(() => {
    const fireAsEvents: RealEvent[] = realFireEvents.map((f) => ({
      id: f.id,
      title: f.title,
      location: 'Active Wildfire',
      lat: f.lat,
      lng: f.lng,
      severity: 'high' as Severity,
      category: 'wildfires',
      timestamp: 'today' as const,
      description: `FRP: ${f.frp}`,
    }));
    const combined = [...realClimateEvents, ...fireAsEvents];
    // Sort: critical first, then high, then medium, then low
    const order: Record<Severity, number> = { critical: 0, high: 1, medium: 2, low: 3 };
    return combined.sort((a, b) => order[a.severity] - order[b.severity]);
  }, [realClimateEvents, realFireEvents]);

  // Count by category
  const catCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const ev of allEvents) {
      counts[ev.category] = (counts[ev.category] || 0) + 1;
    }
    return counts;
  }, [allEvents]);

  const isLive = lastFetch > 0;
  const totalActive = allEvents.length;

  return (
    <BasePanel
      title="Climate Anomalies"
      icon={<Wind size={12} style={{ color: '#60a5fa' }} />}
      badge={
        isLive ? (
          <span className="text-[9px] font-mono animate-pulse" style={{ color: '#34d399' }}>
            ⬤ {totalActive} ACTIVE
          </span>
        ) : undefined
      }
      accentColor="hsl(210 100% 60%)"
    >
      {/* Category summary pills */}
      {Object.keys(catCounts).length > 0 && (
        <div className="px-2 pt-1.5 pb-1 flex flex-wrap gap-1">
          {Object.entries(catCounts).map(([cat, count]) => {
            const cfg = categoryConfig[cat] || { label: cat, Icon: Globe, color: 'text-muted-foreground' };
            return (
              <span
                key={cat}
                className={`text-[9px] font-mono px-1.5 py-0.5 rounded-sm ${cfg.color}`}
                style={{ background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.08)' }}
              >
                {count}× {cfg.label}
              </span>
            );
          })}
        </div>
      )}

      <ScrollArea className="h-[260px] max-h-[300px]">
        <div className="p-2 space-y-1">
          {!isLive || allEvents.length === 0 ? (
            <div className="text-[11px] text-muted-foreground text-center py-6 font-mono">
              {isLive ? 'No active events' : 'Loading EONET data…'}
            </div>
          ) : (
            allEvents.map((ev, i) => {
              const cfg = categoryConfig[ev.category] || { label: ev.category, Icon: Globe, color: 'text-muted-foreground' };
              return (
                <motion.button
                  key={ev.id}
                  initial={{ opacity: 0, x: 10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.025, type: 'spring', stiffness: 300, damping: 28 }}
                  onClick={() => ev.lat && ev.lng && flyTo(ev.lng, ev.lat, 5)}
                  className="event-row w-full text-left"
                >
                  <cfg.Icon size={11} className={`mt-0.5 flex-shrink-0 ${cfg.color}`} />
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] text-foreground/85 truncate leading-snug">{ev.title}</p>
                    <p className="text-[9px] text-muted-foreground/60 font-mono mt-0.5">
                      {cfg.label}{ev.description ? ` · ${ev.description}` : ''}
                    </p>
                  </div>
                  <div
                    className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1 ${severityDot[ev.severity]}`}
                  />
                </motion.button>
              );
            })
          )}
        </div>
      </ScrollArea>
    </BasePanel>
  );
};
