/**
 * LiveNewsPanel — Real-time news feed from GDELT Doc API v2.
 * Globe Monitor LiveNewsPanel — live news headlines from GDELT.
 * News is filtered by the current monitor mode (world/tech/finance/happy).
 * Sentiment tone shown as colored indicator bar.
 */
import { useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Newspaper, ExternalLink, RefreshCw } from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { BasePanel } from './BasePanel';
import { ScrollArea } from '@/components/ui/scroll-area';

const toneBar = (tone: number): string => {
  if (tone < -5) return 'bg-neon-crimson';
  if (tone < -2) return 'bg-neon-amber';
  if (tone > 2)  return 'bg-neon-green';
  return 'bg-muted-foreground';
};

const toneWidth = (tone: number): string => {
  const abs = Math.min(Math.abs(tone), 10);
  return `${abs * 10}%`;
};

const formatDate = (raw: string): string => {
  try {
    const m = raw.match(/^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})/);
    if (m) return `${m[4]}:${m[5]} UTC`;
    return raw.slice(0, 10);
  } catch {
    return '';
  }
};

export const LiveNewsPanel = ({ accentColor = 'hsl(210 100% 55%)' }: { accentColor?: string }) => {
  const mode = useMonitorStore((s) => s.mode);
  const newsArticles = useMonitorStore((s) => s.newsArticles);
  const fetchNews = useMonitorStore((s) => s.fetchNews);

  // Fetch on mount + mode change, then auto-refresh every 90 seconds
  useEffect(() => {
    fetchNews(mode);
    const id = setInterval(() => fetchNews(mode), 90_000);
    return () => clearInterval(id);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mode]);

  const handleRefresh = () => fetchNews(mode);

  const modeLabels: Record<string, string> = {
    world:   'World News',
    tech:    'Tech Intel',
    finance: 'Markets Feed',
    happy:   'Good News',
  };

  return (
    <BasePanel
      title={modeLabels[mode] || 'Live News'}
      icon={<Newspaper size={12} style={{ color: 'hsl(210 100% 55%)' }} />}
      badge={<span className="text-[9px] font-mono animate-pulse" style={{ color: '#34d399' }}>⬤ LIVE</span>}
      accentColor={accentColor}
    >
      <div className="flex items-center justify-between px-3 pb-1 pt-1">
        <span className="text-[9px] font-mono text-foreground/30 tracking-widest">GDELT · 3H</span>
        <button
          onClick={handleRefresh}
          className="text-[9px] font-mono text-foreground/30 hover:text-foreground/60 transition-colors flex items-center gap-1"
        >
          <RefreshCw size={8} />
          SYNC
        </button>
      </div>

      <ScrollArea className="h-[280px] max-h-[320px]">
        <div className="p-2 space-y-1.5">
          <AnimatePresence mode="popLayout">
            {newsArticles.length === 0 ? (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="text-[11px] text-muted-foreground text-center py-6 font-mono"
              >
                Loading news feed…
              </motion.div>
            ) : (
              newsArticles.map((article, i) => (
                <motion.a
                  key={article.url || i}
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ delay: i * 0.03, type: 'spring', stiffness: 300, damping: 28 }}
                  className="block p-1.5 rounded-sm hover:bg-white/5 transition-all group cursor-pointer"
                >
                  <p className="text-[11px] text-foreground/85 leading-snug line-clamp-2 group-hover:text-foreground transition-colors mb-1">
                    {article.title}
                  </p>
                  {/* Tone bar */}
                  <div className="h-0.5 w-full bg-border/20 rounded-full overflow-hidden mb-1">
                    <div
                      className={`h-full rounded-full ${toneBar(article.tone)} transition-all`}
                      style={{ width: toneWidth(article.tone) }}
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] text-muted-foreground font-mono truncate">
                      {article.source}
                    </span>
                    <span className="text-[10px] text-muted-foreground/50 font-mono ml-auto">
                      {formatDate(article.date)}
                    </span>
                    <ExternalLink size={9} className="text-muted-foreground/40 flex-shrink-0" />
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
