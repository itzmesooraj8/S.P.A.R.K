/**
 * MarketTicker — High-frequency scrolling marquee.
 * Uses pure CSS transforms for stutter-free infinite scrolling.
 * Content duplicated for seamless loop.
 */
import { useMemo } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { getTickerForMode } from '@/data/mockData';

export const MarketTicker = () => {
  const mode = useMonitorStore((s) => s.mode);
  const items = useMemo(() => getTickerForMode(mode), [mode]);

  // Duplicate items for seamless CSS infinite scroll
  const allItems = [...items, ...items];

  return (
    <div className="overflow-hidden">
      <div className="flex items-center gap-6 ticker-scroll whitespace-nowrap">
        {allItems.map((item, i) => (
          <div
            key={`${item.symbol}-${i}`}
            className="flex items-center gap-2 text-xs font-mono"
          >
            <span className="text-muted-foreground font-medium">{item.symbol}</span>
            <span className="text-foreground font-semibold">
              {item.value.toLocaleString('en-US', {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
            <span
              className={`flex items-center gap-0.5 font-semibold ${
                item.delta >= 0 ? 'text-neon-green' : 'text-neon-crimson'
              }`}
            >
              {item.delta >= 0 ? <TrendingUp size={10} /> : <TrendingDown size={10} />}
              {item.delta >= 0 ? '+' : ''}
              {item.deltaPercent.toFixed(2)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};
