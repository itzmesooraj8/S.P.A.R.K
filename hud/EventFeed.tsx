import React, { useEffect, useRef, useState } from 'react';
import { useSparkStore } from '../../store/sparkStore';
import HolographicPanel from './HolographicPanel';
import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, Info, ShieldAlert, Cpu, Network, Brain } from 'lucide-react';

const EVENT_CONFIG: Record<string, { color: string; icon: React.ElementType; label: string }> = {
  info:     { color: '#0088FF', icon: Info, label: 'INFO' },
  warning:  { color: '#FFB800', icon: AlertTriangle, label: 'WARN' },
  critical: { color: '#FF3B5C', icon: ShieldAlert, label: 'CRIT' },
  ai:       { color: '#bf5af2', icon: Brain, label: 'AI' },
  system:   { color: '#30d158', icon: Cpu, label: 'SYS' },
  network:  { color: '#00E5FF', icon: Network, label: 'NET' },
  voice:    { color: '#00E5FF', icon: Brain, label: 'AI' },
  web:      { color: '#0088FF', icon: Network, label: 'NET' },
  error:    { color: '#FF3B5C', icon: ShieldAlert, label: 'CRIT' },
};

export default function EventFeed() {
  const agentLog = useSparkStore(state => state.agentLog);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [agentLog]);

  return (
    <HolographicPanel title="SYS.EVENT_FEED" glowColor="#FF3B5C" className="h-full flex flex-col">
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto pr-2 scrollbar-hud flex flex-col gap-2"
      >
        <AnimatePresence initial={false}>
          {agentLog.length === 0 ? (
            <div className="text-white/30 italic font-mono-tech text-[10px] p-2">Monitoring secure channels...</div>
          ) : (
            agentLog.map((log) => {
              const cfg = EVENT_CONFIG[log.type] || EVENT_CONFIG.info;
              const Icon = cfg.icon;
              const timeStr = new Date(log.timestamp).toISOString().split('T')[1].slice(0, 12);

              return (
                <motion.div 
                  key={log.id} 
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  className="flex gap-2 items-start p-2 rounded bg-black/20 border-l-2 backdrop-blur-sm"
                  style={{ borderLeftColor: cfg.color }}
                >
                  <Icon size={12} style={{ color: cfg.color, marginTop: '2px' }} />
                  <div className="flex-1 min-w-0 flex flex-col">
                    <div className="flex justify-between items-center">
                      <span className="font-space text-[9px] font-bold tracking-widest" style={{ color: cfg.color }}>
                        {cfg.label}
                      </span>
                      <span className="font-mono-tech text-[8px] text-white/30">{timeStr}</span>
                    </div>
                    <span className="font-inter text-[11px] text-white/80 leading-snug mt-1 break-words">
                      {log.message}
                    </span>
                  </div>
                </motion.div>
              );
            })
          )}
        </AnimatePresence>
      </div>
    </HolographicPanel>
  );
}
