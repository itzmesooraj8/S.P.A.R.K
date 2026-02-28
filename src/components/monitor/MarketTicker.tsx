/**
 * MarketTicker — High-frequency scrolling HUD marquee.
 * Uses LIVE data from CoinGecko (crypto) + Frankfurter (forex) via S.P.A.R.K backend.
 * Falls back to curated mock tickers while real data loads.
 * Pure CSS transforms for stutter-free infinite scrolling.
 */
import { useMemo } from 'react';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';
import { getTickerForMode } from '@/data/mockData';

interface MarketTickerProps {
  accentColor?: string;
}

export const MarketTicker = ({ accentColor = '#00f5ff' }: MarketTickerProps) => {
  const mode = useMonitorStore((s) => s.mode);
  const realMarketTickers = useMonitorStore((s) => s.realMarketTickers);
  const lastFetch = useMonitorStore((s) => s.lastFetch);

  // Use real tickers when available, otherwise fall back to mock
  const items = useMemo(() => {
    if (lastFetch > 0 && realMarketTickers.length > 0) {
      return realMarketTickers;
    }
    return getTickerForMode(mode);
  }, [realMarketTickers, lastFetch, mode]);

  // Duplicate items for seamless CSS infinite scroll
  const allItems = [...items, ...items, ...items];

  return (
    <div className="overflow-hidden relative" style={{ maskImage: 'linear-gradient(90deg, transparent 0%, black 8%, black 92%, transparent 100%)' }}>
      <div className="flex items-center gap-5 ticker-scroll whitespace-nowrap">
        {allItems.map((item, i) => (
          <div
            key={`${item.symbol}-${i}`}
            className="flex items-center gap-1.5 text-[11px] font-mono shrink-0"
          >
            {/* Separator dot */}
            <span className="text-foreground/20 text-[8px]">◆</span>
            {/* Symbol */}
            <span className="font-bold text-[10px] tracking-widest" style={{ color: accentColor, opacity: 0.7 }}>
              {item.symbol}
            </span>
            {/* Value */}
            <span className="text-foreground/85 font-semibold tabular-nums">
              {item.value > 100
                ? item.value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : item.value.toFixed(4)}
            </span>
            {/* Delta */}
            {item.deltaPercent !== 0 && (
              <span
                className="flex items-center gap-0.5 font-bold text-[10px]"
                style={{ color: item.deltaPercent >= 0 ? '#34d399' : '#f87171' }}
              >
                {item.deltaPercent >= 0 ? <TrendingUp size={9} /> : <TrendingDown size={9} />}
                {item.deltaPercent >= 0 ? '+' : ''}
                {item.deltaPercent.toFixed(2)}%
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
