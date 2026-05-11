import React from 'react';
import { useSparkStore } from '../../store/sparkStore';

export function SysMetrics() {
  const metrics = useSparkStore(state => state.systemMetrics);
  const activeTheme = useSparkStore(state => state.activeTheme);

  if (!metrics) {
    return (
      <div className="hud-panel p-4 flex flex-col gap-2 opacity-50">
        <div className="text-xs uppercase tracking-widest text-gray-400">System Telemetry</div>
        <div className="text-sm font-mono animate-pulse">AWAITING DATA LINK...</div>
      </div>
    );
  }

  const themeColors = {
    cyan: '#00f5ff',
    red: '#ff2a2a',
    amber: '#ffb000',
    white: '#ffffff'
  };
  const color = themeColors[activeTheme];

  return (
    <div className="hud-panel p-4 flex flex-col gap-4">
      <div className={`text-xs uppercase tracking-widest font-bold neon-text-${activeTheme} border-b border-gray-800 pb-2`}>
        System Telemetry
      </div>
      
      <div className="grid grid-cols-2 gap-4">
        {/* CPU */}
        <div className="flex flex-col gap-1">
          <div className="text-xs text-gray-400 font-mono">CPU_LOAD</div>
          <div className="text-2xl font-bold font-mono" style={{ color }}>
            {metrics.cpu.toFixed(1)}%
          </div>
          <div className="w-full h-1 bg-gray-900 mt-1">
            <div className="h-full transition-all duration-500" style={{ width: `${metrics.cpu}%`, backgroundColor: color }} />
          </div>
        </div>

        {/* RAM */}
        <div className="flex flex-col gap-1">
          <div className="text-xs text-gray-400 font-mono">MEM_ALLOC</div>
          <div className="text-2xl font-bold font-mono" style={{ color }}>
            {((1 - metrics.ramFree / metrics.ramTotal) * 100).toFixed(1)}%
          </div>
          <div className="w-full h-1 bg-gray-900 mt-1">
            <div className="h-full transition-all duration-500" style={{ width: `${(1 - metrics.ramFree / metrics.ramTotal) * 100}%`, backgroundColor: color }} />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4 border-t border-gray-800 pt-3">
        {/* DISK */}
        <div className="flex flex-col gap-1">
          <div className="text-[10px] text-gray-500 font-mono">STORAGE</div>
          <div className="text-sm font-mono text-gray-300">
            {metrics.diskFree.toFixed(1)}GB FREE
          </div>
        </div>

        {/* BATTERY */}
        <div className="flex flex-col gap-1">
          <div className="text-[10px] text-gray-500 font-mono">PWR_CELL</div>
          <div className="text-sm font-mono text-gray-300 flex items-center gap-2">
            <span>{metrics.batteryPercent}%</span>
            <div className="w-6 h-3 border border-gray-500 relative flex items-center p-[1px]">
              <div className="h-full bg-green-500" style={{ width: `${metrics.batteryPercent}%` }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
