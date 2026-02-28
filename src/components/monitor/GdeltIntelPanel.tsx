/**
 * GdeltIntelPanel — Intelligence feed from GDELT Doc API v2.
 * Globe Monitor GdeltIntelPanel — GDELT intelligence feed.
 *
 * Topics: military, cyber, nuclear, sanctions, intelligence, maritime, tech, climate
 * Sentiment tone: negative = red, positive = green, neutral = gray
 * Each article links to source. Refreshes when topic changes.
 */
import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Shield, Zap, Atom, Ban, Eye, Anchor, Cpu, Wind,
  ExternalLink, RefreshCw,
} from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { BasePanel } from './BasePanel';
import { ScrollArea } from '@/components/ui/scroll-area';

const TOPICS = [
  { id: 'military',     label: 'Military',     Icon: Shield },
  { id: 'cyber',        label: 'Cyber',        Icon: Zap },
  { id: 'nuclear',      label: 'Nuclear',      Icon: Atom },
  { id: 'sanctions',    label: 'Sanctions',    Icon: Ban },
  { id: 'intelligence', label: 'Intelligence', Icon: Eye },
  { id: 'maritime',     label: 'Maritime',     Icon: Anchor },
  { id: 'tech',         label: 'Tech',         Icon: Cpu },
  { id: 'climate',      label: 'Climate',      Icon: Wind },
] as const;

type TopicId = (typeof TOPICS)[number]['id'];

const toneColor = (tone: number) => {
  if (tone < -5) return 'text-neon-crimson';
  if (tone < -2) return 'text-neon-amber';
  if (tone > 2)  return 'text-neon-green';
  return 'text-muted-foreground';
};

const toneBg = (tone: number) => {
  if (tone < -5) return 'bg-destructive/10';
  if (tone < -2) return 'bg-accent/10';
  if (tone > 2)  return 'bg-neon-green/10';
  return '';
};

/** Format GDELT seendate: "20250228T143000Z" → "14:30 UTC" */
const formatDate = (raw: string): string => {
  try {
    const m = raw.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
    if (m) return `${m[4]}:${m[5]} UTC`;
    return raw.slice(0, 10);
  } catch {
    return '';
  }
};

export const GdeltIntelPanel = ({ accentColor = 'hsl(270 80% 65%)' }: { accentColor?: string }) => {
  const gdeltArticles = useMonitorStore((s) => s.gdeltArticles);
  const intelTopic = useMonitorStore((s) => s.intelTopic);
  const setIntelTopic = useMonitorStore((s) => s.setIntelTopic);
  const fetchGdeltIntel = useMonitorStore((s) => s.fetchGdeltIntel);

  // Load initial topic on mount
  useEffect(() => {
    fetchGdeltIntel(intelTopic);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleTopicClick = (topicId: string) => {
    setIntelTopic(topicId);
  };

  const handleRefresh = () => {
    fetchGdeltIntel(intelTopic);
  };

  const currentTopic = TOPICS.find((t) => t.id === intelTopic);

  return (
    <BasePanel
      title="Intelligence"
      icon={currentTopic ? <currentTopic.Icon size={12} style={{ color: 'hsl(270 80% 65%)' }} /> : undefined}
      badge={
        <span className="text-[9px] font-mono animate-pulse" style={{ color: '#34d399' }}>⬤ GDELT</span>
      }
      accentColor="hsl(270 80% 65%)"
    >
      {/* Topic selector pills */}
      <div className="px-2 pt-2 pb-1 flex flex-wrap gap-1">
        {TOPICS.map(({ id, label, Icon }) => (
          <button
            key={id}
            onClick={() => handleTopicClick(id)}
            className="flex items-center gap-1 px-1.5 py-0.5 rounded text-[9px] font-mono font-bold tracking-wider transition-all"
            style={{
              background: intelTopic === id ? 'rgba(167,139,250,0.15)' : 'rgba(255,255,255,0.04)',
              border: `1px solid ${intelTopic === id ? 'rgba(167,139,250,0.5)' : 'rgba(255,255,255,0.08)'}`,
              color: intelTopic === id ? '#a78bfa' : 'rgba(255,255,255,0.45)',
            }}
          >
            <Icon size={8} />
            {label}
          </button>
        ))}
        <button
          onClick={handleRefresh}
          className="ml-auto flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[9px] font-mono transition-all"
          style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'rgba(255,255,255,0.35)' }}
          title="Refresh"
        >
          <RefreshCw size={8} />
        </button>
      </div>

      <ScrollArea className="h-[300px] max-h-[350px]">
        <div className="p-2 space-y-1.5">
          <AnimatePresence mode="popLayout">
            {gdeltArticles.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-[11px] text-muted-foreground text-center py-6 font-mono"
              >
                Loading intelligence feed…
              </motion.div>
            ) : (
              gdeltArticles.map((article, i) => (
                <motion.a
                  key={article.url || i}
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ delay: i * 0.025, type: 'spring', stiffness: 300, damping: 28 }}
                  className={`block p-1.5 rounded-sm hover:bg-white/5 transition-all group cursor-pointer`}
                >
                  <div className="flex items-start gap-2">
                    {/* Tone indicator */}
                    <div
                      className={`mt-1 w-1.5 h-1.5 rounded-full flex-shrink-0 ${toneColor(article.tone)}`}
                      style={{ backgroundColor: 'currentColor' }}
                    />
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] text-foreground leading-snug line-clamp-2 group-hover:text-primary transition-colors">
                        {article.title}
                      </p>
                      <div className="flex items-center gap-2 mt-0.5">
                        <span className="text-[10px] text-muted-foreground font-mono truncate">
                          {article.source}
                        </span>
                        <span className="text-[10px] text-muted-foreground/60 font-mono">
                          {formatDate(article.date)}
                        </span>
                        <ExternalLink size={9} className="text-muted-foreground/40 flex-shrink-0 ml-auto" />
                      </div>
                    </div>
                  </div>
                </motion.a>
              ))
            )}
          </AnimatePresence>
        </div>
      </ScrollArea>
    </BasePanel>
  );
};
