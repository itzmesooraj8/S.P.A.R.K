/**
 * ThreatMatrix — Left floating panel.
 * Timeline-grouped event feed with severity dots, category icons,
 * and click-to-flyTo interactivity.
 */
import { useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle, Zap, Shield, Globe, Cpu, TrendingUp, Heart,
} from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { getEventsForMode, type MonitorEvent, type Severity } from '@/data/mockData';
import { BasePanel } from './BasePanel';
import { ScrollArea } from '@/components/ui/scroll-area';

const severityClasses: Record<Severity, string> = {
  critical: 'text-neon-crimson',
  high: 'text-neon-amber',
  medium: 'text-accent',
  low: 'text-neon-green',
};

const categoryIcons: Record<string, typeof Globe> = {
  conflict: Shield,
  earthquake: AlertTriangle,
  cyber: Zap,
  political: Globe,
  economic: TrendingUp,
  tech: Cpu,
  climate: Globe,
  positive: Heart,
};

const modeIcons = { world: Globe, tech: Cpu, finance: TrendingUp, happy: Heart };

const timelineLabels: Record<string, string> = {
  today: 'TODAY',
  yesterday: 'YESTERDAY',
  this_week: 'THIS WEEK',
};

export const ThreatMatrix = () => {
  const mode = useMonitorStore((s) => s.mode);
  const flyTo = useMonitorStore((s) => s.flyTo);
  const selectEvent = useMonitorStore((s) => s.selectEvent);
  const selectedEventId = useMonitorStore((s) => s.selectedEventId);

  const events = useMemo(() => getEventsForMode(mode), [mode]);

  /** Group events by timeline period */
  const grouped = useMemo(() => {
    const groups: Record<string, MonitorEvent[]> = {
      today: [],
      yesterday: [],
      this_week: [],
    };
    events.forEach((e) => {
      if (groups[e.timestamp]) groups[e.timestamp].push(e);
    });
    return groups;
  }, [events]);

  const ModeIcon = modeIcons[mode];

  const handleClick = (event: MonitorEvent) => {
    selectEvent(event.id);
    flyTo(event.lng, event.lat, 6);
  };

  return (
    <BasePanel
      title={mode === 'happy' ? 'Good News Feed' : 'Threat Matrix'}
      icon={<ModeIcon size={14} className="text-primary" />}
    >
      <ScrollArea className="h-[calc(100vh-200px)] max-h-[600px]">
        <div className="p-2 space-y-3">
          <AnimatePresence mode="popLayout">
            {Object.entries(grouped).map(
              ([period, items]) =>
                items.length > 0 && (
                  <div key={`${mode}-${period}`}>
                    {/* Timeline header */}
                    <div className="text-[10px] font-mono text-muted-foreground tracking-widest px-2 mb-1.5">
                      {timelineLabels[period]}
                    </div>

                    {/* Event items */}
                    {items.map((event, i) => {
                      const Icon = categoryIcons[event.category] || Globe;
                      const isSelected = selectedEventId === event.id;

                      return (
                        <motion.button
                          key={event.id}
                          initial={{ opacity: 0, x: -20 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -20 }}
                          transition={{
                            delay: i * 0.04,
                            type: 'spring',
                            stiffness: 300,
                            damping: 25,
                          }}
                          onClick={() => handleClick(event)}
                          className={`w-full flex items-start gap-2.5 p-2 rounded-lg text-left transition-all duration-200 hover:bg-secondary/30 ${
                            isSelected
                              ? 'bg-secondary/40 ring-1 ring-primary/30'
                              : ''
                          }`}
                        >
                          {/* Pulsing severity dot */}
                          <div
                            className={`mt-1.5 w-2 h-2 rounded-full flex-shrink-0 ${severityClasses[event.severity]} ${
                              event.severity === 'critical' ? 'pulse-severity' : ''
                            }`}
                            style={{ backgroundColor: 'currentColor' }}
                          />

                          {/* Event info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-1.5">
                              <Icon
                                size={11}
                                className="text-muted-foreground flex-shrink-0"
                              />
                              <span className="text-xs font-medium text-foreground truncate">
                                {event.title}
                              </span>
                            </div>
                            <div className="text-[10px] text-muted-foreground mt-0.5 font-mono">
                              {event.location}
                            </div>
                          </div>

                          {/* Severity badge */}
                          <span
                            className={`text-[9px] font-mono font-bold uppercase tracking-wider ${severityClasses[event.severity]}`}
                          >
                            {event.severity}
                          </span>
                        </motion.button>
                      );
                    })}
                  </div>
                )
            )}
          </AnimatePresence>
        </div>
      </ScrollArea>
    </BasePanel>
  );
};
