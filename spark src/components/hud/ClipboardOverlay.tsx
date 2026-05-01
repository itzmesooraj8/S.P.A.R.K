import React from 'react';
import { useSparkStore } from '../../store/sparkStore';

export function ClipboardOverlay() {
  const assist = useSparkStore(state => state.clipboardAssist);
  
  if (!assist) return null;

  return (
    <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 w-full max-w-lg px-4 pointer-events-none">
      <div className="hud-panel border-cyan-500 bg-[#00121aE6] p-4 flex flex-col shadow-[0_0_20px_rgba(0,243,255,0.2)] animate-in fade-in slide-in-from-bottom-4 duration-500 pointer-events-auto">
        <div className="flex justify-between items-center mb-2">
          <span className="text-[10px] font-bold uppercase tracking-widest text-cyan-500 flex items-center gap-2">
            <span className="w-1.5 h-1.5 bg-cyan-500 rounded-full animate-pulse"></span>
            Contextual Agency Triggered: {assist.type}
          </span>
          <button 
            className="text-cyan-500/50 hover:text-cyan-400 text-[10px] font-mono"
            onClick={() => useSparkStore.getState().setClipboardAssist(null)}
          >
            [IGNORE]
          </button>
        </div>
        
        <div className="font-mono text-cyan-100 text-sm italic mb-2 border-l-2 border-cyan-500/30 pl-3">
          "{assist.offer}"
        </div>
        
        <div className="text-[9px] text-cyan-500/40 font-mono truncate">
          SOURCE: {assist.preview}...
        </div>

        <div className="mt-3 flex gap-2">
          <div className="h-0.5 flex-1 bg-cyan-500/20 overflow-hidden">
            <div className="h-full bg-cyan-500 animate-progress origin-left"></div>
          </div>
        </div>
      </div>
      
      <style jsx>{`
        @keyframes progress {
          from { transform: scaleX(1); }
          to { transform: scaleX(0); }
        }
        .animate-progress {
          animation: progress 8s linear forwards;
        }
      `}</style>
    </div>
  );
}
