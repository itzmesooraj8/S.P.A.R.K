/**
 * ThreatMatrix — Left floating panel.
 * Shows LIVE real-time events (GDELT conflict, USGS earthquakes, NASA EONET,
 * OpenSky military flights). Falls back to curated demo data while loading.
 */
import { useMemo, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle, Zap, Shield, Globe, Cpu, TrendingUp, Heart, Flame, Wind, FolderPlus,
} from 'lucide-react';
import { useMonitorStore, TIME_WINDOW_MS } from '@/store/useMonitorStore';
import { useActivityTracker } from '@/hooks/useActivityTracker';
import type { RealEvent, Severity, TimeWindow } from '@/store/useMonitorStore';
import { getEventsForMode, type MonitorEvent } from '@/data/monitorSeed';
import { BasePanel } from './BasePanel';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ProvenanceTooltip } from './ProvenanceTooltip';

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

const TW_LABELS: Record<TimeWindow, string> = {
  '1h':  '1 HOUR',
  '6h':  '6 HOURS',
  '24h': '24 HOURS',
  '48h': '48 HOURS',
  '7d':  '7 DAYS',
};

/** Apply time-window filter to events that have fetchedAt. Mock events (no fetchedAt) are always kept. */
function applyTimeWindow(
  events: (RealEvent | MonitorEvent)[],
  timeWindow: TimeWindow,
): (RealEvent | MonitorEvent)[] {
  const cutoff = Date.now() - TIME_WINDOW_MS[timeWindow];
  return events.filter((e) => {
    const fetched = (e as any).fetchedAt;
    return !fetched || fetched >= cutoff;
  });
}

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
  const mode            = useMonitorStore((s) => s.mode);
  const flyTo           = useMonitorStore((s) => s.flyTo);
  const selectEvent     = useMonitorStore((s) => s.selectEvent);
  const selectedEventId = useMonitorStore((s) => s.selectedEventId);
  const realWorldEvents  = useMonitorStore((s) => s.realWorldEvents);
  const realCyberEvents  = useMonitorStore((s) => s.realCyberEvents);
  const realFinanceEvents = useMonitorStore((s) => s.realFinanceEvents);
  const realClimateEvents = useMonitorStore((s) => s.realClimateEvents);
  const realEvents      = useMonitorStore((s) => s.realEvents);
  const dataLoading     = useMonitorStore((s) => s.dataLoading);
  const lastFetch       = useMonitorStore((s) => s.lastFetch);
  const addCase         = useMonitorStore((s) => s.addCase);
  const cases           = useMonitorStore((s) => s.cases);
  const openCaseDrawer  = useMonitorStore((s) => s.toggleCaseDrawer);
  const caseDrawerOpen  = useMonitorStore((s) => s.caseDrawerOpen);
  const timeWindow      = useMonitorStore((s) => s.timeWindow);
  const setTimeWindow   = useMonitorStore((s) => s.setTimeWindow);

  const { isNew, observe, newCount } = useActivityTracker();
  const [hoveredEventId, setHoveredEventId] = useState<string | null>(null);

  const isLive = lastFetch > 0;

  const events = useMemo(() => {
    const merged = mergeEvents(realWorldEvents, realCyberEvents, realFinanceEvents, realClimateEvents, realEvents, mode, dataLoading);
    return applyTimeWindow(merged, timeWindow);
  }, [realWorldEvents, realCyberEvents, realFinanceEvents, realClimateEvents, realEvents, mode, dataLoading, timeWindow]);

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

  const handleInvestigate = (e: React.MouseEvent, event: RealEvent | MonitorEvent) => {
    e.stopPropagation();
    addCase({
      id: event.id,
      title: event.title,
      severity: ((event as any).severity || 'medium') as Severity,
      category: (event as any).category || 'conflict',
    });
    if (!caseDrawerOpen) openCaseDrawer();
  };

  const TW_OPTIONS: TimeWindow[] = ['1h', '6h', '24h', '48h', '7d'];

  return (
    <BasePanel
      title={mode === 'happy' ? 'Good News Feed' : 'Threat Matrix'}
      icon={<ModeIcon size={12} style={{ color: accentColor }} />}
      badge={
        <div className="flex items-center gap-1.5">
          {newCount > 0 && (
            <span
              className="text-[8px] font-mono font-bold px-1.5 py-0.5 rounded animate-pulse"
              style={{ background: `${accentColor}18`, color: accentColor, border: `1px solid ${accentColor}40` }}
            >
              +{newCount} NEW
            </span>
          )}
          {isLive && (
            <span className="text-[9px] font-mono" style={{ color: '#34d399' }}>⬤ LIVE</span>
          )}
        </div>
      }
      accentColor={accentColor}
    >
      {/* Time-window selector */}
      <div className="flex items-center gap-0.5 px-2 py-1.5 border-b border-white/5">
        {TW_OPTIONS.map((tw) => (
          <button
            key={tw}
            onClick={() => setTimeWindow(tw)}
            className="flex-1 text-[8px] font-mono font-bold py-0.5 rounded transition-all duration-150"
            style={{
              background: timeWindow === tw ? `${accentColor}20` : 'transparent',
              color: timeWindow === tw ? accentColor : 'rgba(255,255,255,0.25)',
              border: `1px solid ${timeWindow === tw ? `${accentColor}40` : 'transparent'}`,
            }}
          >
            {tw}
          </button>
        ))}
      </div>
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
                      const eventIsNew = isNew(event.id);
                      const alreadyCased = cases.some((c) => c.eventId === event.id);

                      return (
                        <motion.div
                          key={event.id}
                          ref={(el) => observe(el, event.id)}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          transition={{ delay: i * 0.03, type: 'spring', stiffness: 300, damping: 25 }}
                          onClick={() => handleClick(event)}
                          onMouseEnter={() => setHoveredEventId(event.id)}
                          onMouseLeave={() => setHoveredEventId(null)}
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => e.key === 'Enter' && handleClick(event)}
                          className={`event-row w-full text-left transition-all duration-200 group relative ${
                            isSelected ? 'selected' : ''
                          }`}
                        >
                          {/* Provenance tooltip on hover */}
                          {(event as any)._provenance && (
                            <ProvenanceTooltip
                              provenance={(event as any)._provenance}
                              visible={hoveredEventId === event.id}
                            />
                          )}
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
                            <div className="flex items-center gap-1.5">
                              <span className="text-[11px] font-medium text-foreground/90 leading-snug line-clamp-1">
                                {event.title}
                              </span>
                              {/* NEW badge */}
                              {eventIsNew && (
                                <span
                                  className="text-[7px] font-mono font-bold px-1 py-px rounded shrink-0 animate-pulse"
                                  style={{ background: `${accentColor}20`, color: accentColor, border: `1px solid ${accentColor}50` }}
                                >
                                  NEW
                                </span>
                              )}
                            </div>
                            {loc && (
                              <div className="text-[10px] text-muted-foreground/60 font-mono truncate mt-0.5">
                                {loc}
                              </div>
                            )}
                          </div>
                          {/* Investigate button */}
                          <button
                            onClick={(e) => handleInvestigate(e, event)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity p-1 rounded"
                            style={{ color: alreadyCased ? '#34d399' : 'rgba(255,255,255,0.4)' }}
                            title={alreadyCased ? 'Already in cases' : 'Open investigation case'}
                          >
                            <FolderPlus size={10} />
                          </button>
                          {/* Severity chip */}
                          <span
                            className={`text-[9px] font-mono font-bold uppercase tracking-wider shrink-0 px-1 py-0.5 rounded ${severityClasses[sev]}`}
                            style={{ background: 'rgba(255,255,255,0.05)' }}
                          >
                            {sev.slice(0, 3)}
                          </span>
                        </motion.div>
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
