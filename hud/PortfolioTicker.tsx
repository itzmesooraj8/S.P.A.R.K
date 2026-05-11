import React, { useEffect, useRef } from 'react';
import { useSparkStore } from '../../store/sparkStore';

export function PortfolioTicker() {
  const portfolio = useSparkStore(state => state.portfolio);
  const activeTheme = useSparkStore(state => state.activeTheme);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (portfolio.length > 4 && scrollRef.current) {
      let scrollAmount = 0;
      const interval = setInterval(() => {
        if (scrollRef.current) {
          scrollRef.current.scrollTop = scrollAmount;
          scrollAmount += 1;
          if (scrollAmount >= scrollRef.current.scrollHeight / 2) {
            scrollAmount = 0;
          }
        }
      }, 50);
      return () => clearInterval(interval);
    }
  }, [portfolio.length]);

  if (!portfolio || portfolio.length === 0) {
    return (
      <div className="hud-panel p-3 border-l-2 border-gray-700">
        <div className="text-[10px] uppercase font-mono text-gray-500 mb-1 tracking-widest">ASSET_TRACKER</div>
        <div className="text-sm font-mono text-gray-600">NO POSITIONS HELD</div>
      </div>
    );
  }

  const totalValue = portfolio.reduce((acc, pos) => acc + (pos.qty * pos.currentPrice), 0);
  const totalInvested = portfolio.reduce((acc, pos) => acc + (pos.qty * pos.buyPrice), 0);
  const totalPnl = totalValue - totalInvested;
  const totalPnlPercent = totalInvested ? (totalPnl / totalInvested) * 100 : 0;

  return (
    <div className="hud-panel p-3 flex flex-col h-full border-l-2 border-gray-700">
      <div className="flex justify-between items-end mb-3 border-b border-gray-800 pb-2">
        <div className="text-[10px] uppercase font-mono text-gray-400 tracking-widest">ASSET_TRACKER</div>
        <div className="text-right">
          <div className="text-lg font-bold font-mono">₹{totalValue.toLocaleString(undefined, {maximumFractionDigits:0})}</div>
          <div className={`text-xs font-mono font-bold ${totalPnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            {totalPnl >= 0 ? '▲' : '▼'} ₹{Math.abs(totalPnl).toLocaleString(undefined, {maximumFractionDigits:0})} ({Math.abs(totalPnlPercent).toFixed(2)}%)
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-hidden relative">
        <div 
          ref={scrollRef}
          className="h-full overflow-y-auto no-scrollbar flex flex-col gap-2"
          style={{ scrollBehavior: 'smooth' }}
        >
          {portfolio.map((pos, idx) => {
            const isUp = pos.pnl >= 0;
            return (
              <div key={`${pos.symbol}-${idx}`} className="flex justify-between items-center text-sm font-mono bg-[#00000033] p-2 border-l border-gray-800">
                <div className="flex flex-col">
                  <span className="font-bold text-gray-200">{pos.symbol}</span>
                  <span className="text-[10px] text-gray-500">{pos.qty} SHRS @ {pos.buyPrice}</span>
                </div>
                <div className="text-right flex flex-col">
                  <span className="text-gray-300">₹{pos.currentPrice.toLocaleString()}</span>
                  <span className={`text-[10px] font-bold ${isUp ? 'text-green-400' : 'text-red-400'}`}>
                    {isUp ? '+' : ''}{pos.pnlPercent.toFixed(2)}%
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <style>{`.no-scrollbar::-webkit-scrollbar { display: none; }`}</style>
    </div>
  );
}
