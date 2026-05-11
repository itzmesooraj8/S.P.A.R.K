/**
 * ToolActivityPanel — HUD module
 * ─────────────────────────────────────────────────────────────────────────────
 * Live feed of TOOL_EXECUTE / TOOL_RESULT frames from the AI reasoning engine.
 * Opened via BottomDock "TOOLS" button.
 */

import { Cpu, CheckCircle, XCircle, Loader, Trash2, ChevronDown, ChevronRight } from 'lucide-react';
import { useState } from 'react';
import { useToolActivityStore, ToolEvent } from '@/store/useToolActivityStore';
import { motion, AnimatePresence } from 'framer-motion';

function ToolRow({ event }: { event: ToolEvent }) {
  const [expanded, setExpanded] = useState(false);

  const isExecute = event.type === 'TOOL_EXECUTE';
  const color =
    event.status === 'running'  ? '#00f5ff' :
    event.status === 'success'  ? '#30d158' :
    event.status === 'error'    ? '#ff2d55' : '#00f5ff';

  const icon =
    event.status === 'running' ? <Loader size={10} className="animate-spin" style={{ color }} /> :
    event.status === 'success' ? <CheckCircle size={10} style={{ color }} /> :
    event.status === 'error'   ? <XCircle size={10} style={{ color }} /> :
    <Cpu size={10} style={{ color }} />;

  const hasDetail = (event.output ?? event.error ?? (event.arguments && Object.keys(event.arguments).length > 0));

  return (
    <div
      className="rounded border mb-1.5 overflow-hidden transition-all"
      style={{ borderColor: `${color}25`, background: `${color}06` }}
    >
      <div
        className="flex items-center gap-2 px-2 py-1.5 cursor-pointer select-none"
        onClick={() => hasDetail && setExpanded(v => !v)}
      >
        {icon}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="font-orbitron text-[9px]" style={{ color }}>
              {isExecute ? '▶ EXEC' : '◀ RESULT'}
            </span>
            <span className="font-mono-tech text-[10px] text-white/80 truncate">{event.tool}</span>
          </div>
        </div>
        <span className="font-mono-tech text-[8px] text-white/25 flex-shrink-0">
          {new Date(event.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
        </span>
        {hasDetail && (
          <span className="text-white/30 flex-shrink-0">
            {expanded ? <ChevronDown size={10} /> : <ChevronRight size={10} />}
          </span>
        )}
      </div>

      <AnimatePresence>
        {expanded && hasDetail && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-2 border-t" style={{ borderColor: `${color}15` }}>
              {/* Arguments */}
              {event.arguments && Object.keys(event.arguments).length > 0 && (
                <div className="mt-1.5">
                  <div className="font-orbitron text-[8px] text-white/30 mb-1 tracking-widest uppercase">Args</div>
                  <pre className="font-mono-tech text-[8px] text-hud-cyan/60 whitespace-pre-wrap break-all leading-4 max-h-24 overflow-y-auto">
                    {JSON.stringify(event.arguments, null, 2)}
                  </pre>
                </div>
              )}

              {/* Output */}
              {event.output && (
                <div className="mt-1.5">
                  <div className="font-orbitron text-[8px] text-white/30 mb-1 tracking-widest uppercase">Output</div>
                  <div className="font-mono-tech text-[8px] text-hud-green/70 leading-4 max-h-20 overflow-y-auto whitespace-pre-wrap break-all">
                    {event.output.slice(0, 400)}{event.output.length > 400 ? '…' : ''}
                  </div>
                </div>
              )}

              {/* Error */}
              {event.error && (
                <div className="mt-1.5">
                  <div className="font-orbitron text-[8px] text-hud-red/50 mb-1 tracking-widest uppercase">Error</div>
                  <div className="font-mono-tech text-[8px] text-hud-red/70 leading-4 max-h-16 overflow-y-auto whitespace-pre-wrap break-all">
                    {event.error}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Panel ─────────────────────────────────────────────────────────────────────
export default function ToolActivityPanel() {
  const { events, pendingTools, clearAll } = useToolActivityStore();

  return (
    <div className="h-full flex flex-col p-3 gap-2 font-mono-tech">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu size={12} className="text-hud-cyan/70" />
          <span className="font-orbitron text-[10px] neon-text tracking-widest">TOOL EXECUTION</span>
          {pendingTools.size > 0 && (
            <span
              className="font-orbitron text-[8px] px-1.5 py-0.5 rounded border animate-pulse"
              style={{ borderColor: '#00f5ff50', color: '#00f5ff', background: '#00f5ff15' }}
            >
              {pendingTools.size} RUNNING
            </span>
          )}
        </div>
        <button
          onClick={clearAll}
          className="flex items-center gap-1 text-[8px] text-white/30 hover:text-hud-red/80 transition-colors"
        >
          <Trash2 size={10} />
          CLEAR
        </button>
      </div>

      {/* Active tools summary */}
      {pendingTools.size > 0 && (
        <div
          className="rounded border border-hud-cyan/20 bg-hud-cyan/5 px-2 py-1.5 flex flex-wrap gap-1"
        >
          {Array.from(pendingTools).map(t => (
            <span
              key={t}
              className="font-mono-tech text-[8px] px-1.5 py-0.5 rounded border border-hud-cyan/30 text-hud-cyan/80 bg-hud-cyan/10 flex items-center gap-1"
            >
              <Loader size={7} className="animate-spin" />
              {t}
            </span>
          ))}
        </div>
      )}

      {/* Event list */}
      <div className="flex-1 overflow-y-auto pr-1 custom-scroll">
        {events.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-32 gap-2 text-white/20">
            <Cpu size={24} />
            <span className="text-[9px] tracking-widest">NO TOOL EVENTS</span>
          </div>
        ) : (
          events.map(ev => <ToolRow key={ev.id} event={ev} />)
        )}
      </div>
    </div>
  );
}
