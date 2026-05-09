import React from 'react';
import { useSystemMetrics } from '@/hooks/useSystemMetrics';
import HolographicPanel from './HolographicPanel';

export default function SystemTelemetry() {
  const metrics = useSystemMetrics();

  return (
    <HolographicPanel title="SYS.TELEMETRY" glowColor="#00E5FF" className="h-full flex flex-col gap-3 text-white">
      
      {/* CPU */}
      <div className="flex flex-col gap-1">
        <div className="flex justify-between font-mono-tech text-[10px] text-[#00E5FF]/70">
          <span>CPU_CORE_LOAD</span>
          <span>{metrics.cpu.toFixed(1)}%</span>
        </div>
        <div className="w-full h-1.5 bg-[#00E5FF]/10 rounded-full overflow-hidden">
          <div 
            className="h-full rounded-full transition-all duration-300"
            style={{ 
              width: `${metrics.cpu}%`, 
              background: '#00E5FF', 
              boxShadow: '0 0 10px #00E5FF' 
            }} 
          />
        </div>
      </div>

      {/* RAM */}
      <div className="flex flex-col gap-1">
        <div className="flex justify-between font-mono-tech text-[10px] text-[#00E5FF]/70">
          <span>MEM_ALLOCATION</span>
          <span>{metrics.ram.toFixed(1)}%</span>
        </div>
        <div className="w-full h-1.5 bg-[#00E5FF]/10 rounded-full overflow-hidden">
          <div 
            className="h-full rounded-full transition-all duration-300"
            style={{ 
              width: `${metrics.ram}%`, 
              background: '#00E5FF', 
              boxShadow: '0 0 10px #00E5FF' 
            }} 
          />
        </div>
      </div>

      {/* Network / Ping */}
      <div className="flex flex-col gap-1">
        <div className="flex justify-between font-mono-tech text-[10px] text-[#00E5FF]/70">
          <span>UPLINK_LATENCY</span>
          <span>{metrics.ping}ms</span>
        </div>
        <div className="w-full flex gap-[2px] mt-1">
          {Array.from({ length: 20 }).map((_, i) => (
            <div 
              key={i} 
              className="flex-1 h-2 transition-all duration-75"
              style={{
                background: i < (20 - Math.min(20, Math.floor(metrics.ping / 10))) ? '#00E5FF' : '#00E5FF20',
                boxShadow: i < (20 - Math.min(20, Math.floor(metrics.ping / 10))) ? '0 0 5px #00E5FF' : 'none'
              }}
            />
          ))}
        </div>
      </div>

      {/* Animated Data Stream */}
      <div className="flex-1 min-h-[40px] mt-2 relative overflow-hidden border border-[#00E5FF]/20 bg-[#00E5FF]/5 rounded">
        <div 
          className="absolute inset-0 font-mono-tech text-[8px] leading-3 text-[#00E5FF]/40 p-2 break-all"
          style={{
            maskImage: 'linear-gradient(180deg, transparent, black 20%, black 80%, transparent)'
          }}
        >
          {Array.from({ length: 15 }).map((_, i) => (
            <div key={i} className="animate-pulse" style={{ animationDelay: `${i * 0.1}s` }}>
              0x{Math.floor(Math.random() * 16777215).toString(16).toUpperCase().padStart(6, '0')} ... 
              {Math.random() > 0.5 ? 'OK' : 'SYN'}
            </div>
          ))}
        </div>
      </div>

    </HolographicPanel>
  );
}
