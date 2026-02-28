/**
 * ThreatMatrix — Left floating panel.
 * Shows LIVE real-time events (GDELT conflict, USGS earthquakes, NASA EONET,
 * OpenSky military flights). Falls back to curated demo data while loading.
 */
import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle, Zap, Shield, Globe, Cpu, TrendingUp, Heart, Flame, Wind,
} from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import type { RealEvent, Severity } from '@/store/useMonitorStore';
import { getEventsForMode, type MonitorEvent } from '@/data/mockData';
import { BasePanel } from './BasePanel';
import { ScrollArea } from '@/components/ui/scroll-area';

const severityClasses: Record<Severity, string> = {
  critical: 'text-neon-crimson',
  high: 'text-neon-amber',
  medium: 'text-accent',
  low: 'text-neon-green',
};

const categoryIcons: Record<string, typeof Globe> = {
  conflict:   Shield,
  earthquake: AlertTriangle,
  cyber:      Zap,
  political:  Globe,
  economic:   TrendingUp,
  tech:       Cpu,
  climate:    Wind,
  wildfire:   Flame,
  positive:   Heart,
};

const modeIcons = { world: Globe, tech: Cpu, finance: TrendingUp, happy: Heart };

const timelineLabels: Record<string, string> = {
  today:     'TODAY',
  yesterday: 'YESTERDAY',
  this_week: 'THIS WEEK',
};

/** Merge real events (from store) with mock fallback; deduplicate by id. */
function mergeEvents(
  realWorldEvents: RealEvent[],
  realCyberEvents: RealEvent[],
  realFinanceEvents: RealEvent[],
  realClimateEvents: RealEvent[],
  realEvents: RealEvent[],        // earthquakes + military flights
  mode: string,
  dataLoading: boolean,
): (RealEvent | MonitorEvent)[] {
  let candidates: (RealEvent | MonitorEvent)[] = [];

  switch (mode) {
    case 'world':
      // Real GDELT conflict + real earthquakes/flights
      candidates = [...realWorldEvents, ...realEvents];
      break;
    case 'tech':
      candidates = realCyberEvents;
      break;
    case 'finance':
      candidates = realFinanceEvents;
      break;
    case 'happy':
      // No good free API for "happy" events — always use curated mock
      candidates = [];
      break;
  }

  // If we have real data, use it; otherwise fall back to curated mock
  if (candidates.length === 0) {
    return getEventsForMode(mode as any);
  }

  // Deduplicate by id
  const seen = new Set<string>();
  const result: (RealEvent | MonitorEvent)[] = [];
  for (const ev of candidates) {
    if (!seen.has(ev.id)) {
      seen.add(ev.id);
      result.push(ev);
    }
  }

  // Supplement with mock if we have < 5 events
  if (result.length < 5) {
    for (const ev of getEventsForMode(mode as any)) {
      if (!seen.has(ev.id)) {
        seen.add(ev.id);
        result.push(ev);
        if (result.length >= 10) break;
      }
    }
  }

  return result;
}

export const ThreatMatrix = ({ accentColor = 'hsl(186 100% 50%)' }: { accentColor?: string }) => {
  const mode = useMonitorStore((s) => s.mode);
  const flyTo = useMonitorStore((s) => s.flyTo);
  const selectEvent = useMonitorStore((s) => s.selectEvent);
  const selectedEventId = useMonitorStore((s) => s.selectedEventId);
  const realWorldEvents = useMonitorStore((s) => s.realWorldEvents);
  const realCyberEvents = useMonitorStore((s) => s.realCyberEvents);
  const realFinanceEvents = useMonitorStore((s) => s.realFinanceEvents);
  const realClimateEvents = useMonitorStore((s) => s.realClimateEvents);
  const realEvents = useMonitorStore((s) => s.realEvents);
  const dataLoading = useMonitorStore((s) => s.dataLoading);
  const lastFetch = useMonitorStore((s) => s.lastFetch);

  const isLive = lastFetch > 0;

  const events = useMemo(
    () => mergeEvents(realWorldEvents, realCyberEvents, realFinanceEvents, realClimateEvents, realEvents, mode, dataLoading),
    [realWorldEvents, realCyberEvents, realFinanceEvents, realClimateEvents, realEvents, mode, dataLoading],
  );

  /** Group events by timeline period */
  const grouped = useMemo(() => {
    const groups: Record<string, (RealEvent | MonitorEvent)[]> = {
      today: [], yesterday: [], this_week: [],
    };
    events.forEach((e) => {
      const ts = (e as any).timestamp || 'today';
      if (groups[ts]) groups[ts].push(e);
      else groups.today.push(e);
    });
    return groups;
  }, [events]);

  const ModeIcon = modeIcons[mode];

  const handleClick = (event: RealEvent | MonitorEvent) => {
    selectEvent(event.id);
    const lat = (event as any).lat ?? 0;
    const lng = (event as any).lng ?? 0;
    if (lat !== 0 || lng !== 0) flyTo(lng, lat, 6);
  };

  return (
    <BasePanel
      title={mode === 'happy' ? 'Good News Feed' : 'Threat Matrix'}
      icon={<ModeIcon size={12} style={{ color: accentColor }} />}
      badge={isLive ? <span className="text-[9px] font-mono animate-pulse" style={{ color: '#34d399' }}>⬤ LIVE</span> : undefined}
      accentColor={accentColor}
    >
      <ScrollArea className="max-h-[380px]">
        <div className="p-2 space-y-3">
          <AnimatePresence mode="popLayout">
            {Object.entries(grouped).map(
              ([period, items]) =>
                items.length > 0 && (
                  <div key={`${mode}-${period}`}>
                    {/* Timeline section divider */}
                    <div className="hud-section-label mb-1">
                      {timelineLabels[period]}
                    </div>

                    {items.map((event, i) => {
                      const sev = ((event as any).severity || 'medium') as Severity;
                      const cat = (event as any).category || 'conflict';
                      const Icon = categoryIcons[cat] || Globe;
                      const isSelected = selectedEventId === event.id;
                      const loc = (event as any).location || '';

                      return (
                        <motion.button
                          key={event.id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          transition={{ delay: i * 0.03, type: 'spring', stiffness: 300, damping: 25 }}
                          onClick={() => handleClick(event)}
                          className={`event-row w-full text-left transition-all duration-200 ${
                            isSelected ? 'selected' : ''
                          }`}
                        >
                          {/* Pulsing severity dot */}
                          {/* Left severity stripe */}
                          <div
                            className={`self-stretch w-0.5 rounded-full flex-shrink-0 ${
                              sev === 'critical' ? 'severity-bar-critical pulse-severity' :
                              sev === 'high' ? 'severity-bar-high' :
                              sev === 'medium' ? 'severity-bar-medium' : 'severity-bar-low'
                            }`}
                            style={{ minHeight: '28px' }}
                          />
                          {/* Icon */}
                          <Icon size={11} className={`mt-0.5 flex-shrink-0 ${severityClasses[sev]}`} />
                          {/* Event info */}
                          <div className="flex-1 min-w-0">
                            <span className="text-[11px] font-medium text-foreground/90 leading-snug line-clamp-2">
                              {event.title}
                            </span>
                            {loc && (
                              <div className="text-[10px] text-muted-foreground/60 font-mono truncate mt-0.5">
                                {loc}
                              </div>
                            )}
                          </div>
                          {/* Severity chip */}
                          <span
                            className={`text-[9px] font-mono font-bold uppercase tracking-wider shrink-0 px-1 py-0.5 rounded ${severityClasses[sev]}`}
                            style={{ background: 'rgba(255,255,255,0.05)' }}
                          >
                            {sev.slice(0, 3)}
                          </span>
                        </motion.button>
                      );
                    })}
                  </div>
                ),
            )}
          </AnimatePresence>
        </div>
      </ScrollArea>
    </BasePanel>
  );
};
