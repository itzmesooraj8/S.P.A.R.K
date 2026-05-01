/**
 * CustomMonitorPanel — User-defined keyword monitors.
 * Persists to localStorage via Zustand persist middleware.
 * Each monitor has a keyword, a custom color, enable/disable toggle,
 * and shows a live match count from the current data fetch.
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, X, ToggleRight, Eye, EyeOff } from 'lucide-react';
import { useMonitorStore, type CustomMonitor } from '@/store/useMonitorStore';
import { BasePanel } from './BasePanel';

/** Preset palette for quick color selection */
const PALETTE = [
  '#f87171', '#fb923c', '#fbbf24', '#a3e635',
  '#34d399', '#22d3ee', '#60a5fa', '#a78bfa',
  '#f472b6', '#ffffff',
];

interface CustomMonitorPanelProps {
  accentColor?: string;
}

export const CustomMonitorPanel = ({ accentColor = '#00f5ff' }: CustomMonitorPanelProps) => {
  const customMonitors         = useMonitorStore((s) => s.customMonitors);
  const addCustomMonitor       = useMonitorStore((s) => s.addCustomMonitor);
  const toggleCustomMonitor    = useMonitorStore((s) => s.toggleCustomMonitor);
  const removeCustomMonitor    = useMonitorStore((s) => s.removeCustomMonitor);

  const [keyword, setKeyword] = useState('');
  const [color,   setColor]   = useState(PALETTE[6]);
  const [adding,  setAdding]  = useState(false);

  const handleAdd = () => {
    const trimmed = keyword.trim();
    if (!trimmed) return;
    addCustomMonitor(trimmed, color);
    setKeyword('');
    setAdding(false);
  };

  return (
    <BasePanel
      title="CUSTOM MONITORS"
      icon={<ToggleRight size={13} />}
      accentColor={accentColor}
      defaultCollapsed={false}
    >
      <div className="space-y-1">
        {/* Monitor list */}
        {customMonitors.length === 0 && !adding && (
          <p className="text-[10px] font-mono text-foreground/30 text-center py-3">
            No monitors. Add a keyword to track.
          </p>
        )}

        <AnimatePresence initial={false}>
          {customMonitors.map((m: CustomMonitor) => (
            <motion.div
              key={m.id}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              transition={{ duration: 0.15 }}
              className="flex items-center gap-2 px-2 py-1.5 rounded group"
              style={{
                background: m.enabled ? `${m.color}08` : 'rgba(255,255,255,0.02)',
                border: `1px solid ${m.enabled ? m.color + '25' : 'rgba(255,255,255,0.06)'}`,
              }}
            >
              {/* Color dot */}
              <span
                className="w-2 h-2 rounded-full shrink-0"
                style={{
                  background: m.color,
                  boxShadow: m.enabled ? `0 0 6px ${m.color}` : 'none',
                  opacity: m.enabled ? 1 : 0.4,
                }}
              />

              {/* Keyword */}
              <span
                className="flex-1 text-[10px] font-mono font-bold truncate"
                style={{ color: m.enabled ? m.color : 'rgba(255,255,255,0.3)' }}
              >
                {m.keyword}
              </span>

              {/* Match count badge */}
              {m.matchCount > 0 && (
                <span
                  className="text-[9px] font-mono font-bold px-1.5 py-0.5 rounded"
                  style={{
                    background: `${m.color}20`,
                    color: m.color,
                    border: `1px solid ${m.color}40`,
                  }}
                >
                  {m.matchCount}
                </span>
              )}

              {/* Toggle */}
              <button
                onClick={() => toggleCustomMonitor(m.id)}
                className="opacity-0 group-hover:opacity-100 transition-opacity"
                style={{ color: m.enabled ? m.color : 'rgba(255,255,255,0.3)' }}
                title={m.enabled ? 'Disable' : 'Enable'}
              >
                {m.enabled ? <Eye size={11} /> : <EyeOff size={11} />}
              </button>

              {/* Remove */}
              <button
                onClick={() => removeCustomMonitor(m.id)}
                className="opacity-0 group-hover:opacity-100 transition-opacity text-foreground/30 hover:text-red-400"
                title="Remove monitor"
              >
                <X size={11} />
              </button>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Add form */}
        <AnimatePresence>
          {adding && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="space-y-2 pt-1"
            >
              <input
                type="text"
                value={keyword}
                onChange={(e) => setKeyword(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') handleAdd();
                  if (e.key === 'Escape') setAdding(false);
                }}
                placeholder="keyword to monitor…"
                autoFocus
                className="w-full px-2 py-1.5 text-[10px] font-mono rounded outline-none"
                style={{
                  background: 'rgba(255,255,255,0.05)',
                  border: `1px solid ${accentColor}30`,
                  color: '#e2e8f0',
                  caretColor: accentColor,
                }}
              />

              {/* Color palette */}
              <div className="flex gap-1 flex-wrap">
                {PALETTE.map((c) => (
                  <button
                    key={c}
                    onClick={() => setColor(c)}
                    className="w-4 h-4 rounded-sm transition-all"
                    style={{
                      background: c,
                      transform: color === c ? 'scale(1.25)' : 'scale(1)',
                      boxShadow: color === c ? `0 0 6px ${c}` : 'none',
                      outline: color === c ? `1px solid ${c}` : 'none',
                    }}
                  />
                ))}
              </div>

              <div className="flex gap-1">
                <button
                  onClick={handleAdd}
                  className="flex-1 py-1 text-[9px] font-mono font-bold rounded transition-all"
                  style={{
                    background: `${accentColor}20`,
                    border: `1px solid ${accentColor}50`,
                    color: accentColor,
                  }}
                >
                  ADD MONITOR
                </button>
                <button
                  onClick={() => setAdding(false)}
                  className="px-2 py-1 text-[9px] font-mono font-bold rounded text-foreground/40 hover:text-foreground/70 transition-all"
                  style={{ border: '1px solid rgba(255,255,255,0.08)' }}
                >
                  CANCEL
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Add button */}
        {!adding && (
          <button
            onClick={() => setAdding(true)}
            className="w-full flex items-center justify-center gap-1.5 py-1.5 text-[9px] font-mono font-bold rounded transition-all mt-1 hover:opacity-80"
            style={{
              background: `${accentColor}08`,
              border: `1px dashed ${accentColor}30`,
              color: `${accentColor}80`,
            }}
          >
            <Plus size={10} />
            ADD KEYWORD MONITOR
          </button>
        )}
      </div>
    </BasePanel>
  );
};
