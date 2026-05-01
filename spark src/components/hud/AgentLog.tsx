import React, { useEffect, useRef } from 'react';
import { useSparkStore } from '../../store/sparkStore';

export function AgentLog() {
  const agentLog = useSparkStore(state => state.agentLog);
  const activeTheme = useSparkStore(state => state.activeTheme);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [agentLog]);

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'voice': return 'text-cyan-400';
      case 'web': return 'text-amber-400';
      case 'system': return 'text-green-400';
      case 'error': return 'text-red-500';
      default: return 'text-gray-400';
    }
  };

  return (
    <div className="hud-panel p-4 flex flex-col h-full bg-[#020813] border border-[#00f5ff20]">
      <div className="flex justify-between items-center mb-2 border-b border-[#00f5ff20] pb-2">
        <div className={`text-xs uppercase tracking-widest font-bold neon-text-${activeTheme}`}>
          Agent Activity Stream
        </div>
        <div className="text-[10px] text-gray-500 font-mono tracking-widest">
          SYS.LOG
        </div>
      </div>

      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto font-mono text-xs flex flex-col gap-1 pr-2 no-scrollbar"
      >
        {agentLog.length === 0 ? (
          <div className="text-gray-600 italic">Awaiting events...</div>
        ) : (
          agentLog.map((log) => {
            const timeStr = new Date(log.timestamp).toISOString().split('T')[1].slice(0, 12);
            return (
              <div key={log.id} className="flex gap-3 hover:bg-[#ffffff05] p-1 border-l-2 border-transparent hover:border-gray-600 transition-colors">
                <span className="text-gray-600 w-[100px] flex-shrink-0">[{timeStr}]</span>
                <span className={`w-[60px] uppercase flex-shrink-0 font-bold ${getTypeColor(log.type)}`}>
                  {log.type}
                </span>
                <span className="text-gray-300 break-words">{log.message}</span>
              </div>
            );
          })
        )}
      </div>
      <style>{`.no-scrollbar::-webkit-scrollbar { width: 4px; } .no-scrollbar::-webkit-scrollbar-thumb { background: #333; }`}</style>
    </div>
  );
}
