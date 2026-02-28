/**
 * TopBar — S.P.A.R.K World Monitor V2 top HUD bar.
 * Features:
 *   - SPARK brand glyph + system ID (Orbitron)
 *   - Mode switcher with per-mode accent color (cyan/purple/amber/green)
 *   - Live UTC clock (updates every second)
 *   - Real-time market ticker
 *   - Panel toggle buttons
 */
import { useEffect, useState } from 'react';
import { Globe, Cpu, TrendingUp, Heart, PanelLeftClose, PanelRightClose, Radio } from 'lucide-react';
import { motion } from 'framer-motion';
import { useMonitorStore, type MonitorMode } from '@/store/useMonitorStore';
import { MarketTicker } from './MarketTicker';

const MODES: { id: MonitorMode; label: string; icon: typeof Globe; color: string; dimColor: string }[] = [
  { id: 'world',   label: 'WORLD',   icon: Globe,       color: '#00f5ff', dimColor: 'rgba(0,245,255,0.12)' },
  { id: 'tech',    label: 'TECH',    icon: Cpu,         color: '#a78bfa', dimColor: 'rgba(167,139,250,0.12)' },
  { id: 'finance', label: 'FINANCE', icon: TrendingUp,  color: '#fbbf24', dimColor: 'rgba(251,191,36,0.12)' },
  { id: 'happy',   label: 'HAPPY',   icon: Heart,       color: '#34d399', dimColor: 'rgba(52,211,153,0.12)' },
];

export const TopBar = () => {
  const mode = useMonitorStore((s) => s.mode);
  const setMode = useMonitorStore((s) => s.setMode);
  const toggleLeftPanel = useMonitorStore((s) => s.toggleLeftPanel);
  const toggleRightPanel = useMonitorStore((s) => s.toggleRightPanel);
  const dataLoading = useMonitorStore((s) => s.dataLoading);

  const [utcTime, setUtcTime] = useState('');
  const [utcDate, setUtcDate] = useState('');

  useEffect(() => {
    const tick = () => {
      const now = new Date();
      setUtcTime(now.toISOString().slice(11, 19));
      setUtcDate(now.toISOString().slice(0, 10));
    };
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, []);

  const activeMode = MODES.find((m) => m.id === mode) ?? MODES[0];

  return (
    <motion.div
      className="fixed top-0 left-0 right-0 z-50"
      initial={{ y: -60 }}
      animate={{ y: 0 }}
      transition={{ type: 'spring', stiffness: 210, damping: 28 }}
      style={{
        background: 'linear-gradient(180deg, rgba(1, 8, 20, 0.97) 0%, rgba(2, 12, 26, 0.88) 100%)',
        backdropFilter: 'blur(24px) saturate(1.2)',
        borderBottom: `1px solid ${activeMode.color}28`,
        boxShadow: `0 1px 24px ${activeMode.color}14, inset 0 -1px 0 rgba(255,255,255,0.04)`,
        transition: 'border-color 0.4s, box-shadow 0.4s',
      }}
    >
      {/* ── Top accent glow line ─────────────────────────────────── */}
      <motion.div
        className="h-px w-full"
        animate={{ opacity: [0.5, 0.9, 0.5] }}
        transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          background: `linear-gradient(90deg, transparent 0%, ${activeMode.color}70 30%, ${activeMode.color}90 50%, ${activeMode.color}70 70%, transparent 100%)`,
        }}
      />

      <div className="flex items-center h-12 px-3 gap-2.5">

        {/* ── Left panel toggle ──────────────────────────────────── */}
        <button
          onClick={toggleLeftPanel}
          className="flex items-center justify-center w-7 h-7 rounded shrink-0 transition-all duration-200 hover:bg-white/10"
          style={{ color: `${activeMode.color}80` }}
          title="Toggle left panel"
        >
          <PanelLeftClose size={15} />
        </button>

        {/* ── SPARK Brand ───────────────────────────────────────── */}
        <div className="hidden lg:flex items-center gap-2 shrink-0 mr-1">
          {/* Glyph icon */}
          <div className="relative w-6 h-6 shrink-0">
            <div
              className="absolute inset-0 rounded-sm"
              style={{
                border: `1px solid ${activeMode.color}50`,
                background: `${activeMode.color}08`,
                boxShadow: `inset 0 0 8px ${activeMode.color}20, 0 0 8px ${activeMode.color}20`,
              }}
            />
            <div
              className="absolute inset-0 flex items-center justify-center"
            >
              <div
                className="w-2 h-2 rounded-sm"
                style={{
                  background: activeMode.color,
                  boxShadow: `0 0 8px ${activeMode.color}`,
                  animation: 'pulse-glow 2.5s ease-in-out infinite',
                }}
              />
            </div>
          </div>
          <div className="flex flex-col">
            <span
              className="text-[11px] font-bold tracking-[0.3em] font-orbitron leading-none"
              style={{
                color: activeMode.color,
                textShadow: `0 0 8px ${activeMode.color}80, 0 0 20px ${activeMode.color}40`,
              }}
            >
              S.P.A.R.K
            </span>
            <span className="text-[7px] font-mono text-foreground/30 tracking-[0.2em] leading-none mt-0.5">
              WORLD MONITOR V2
            </span>
          </div>
          {/* Divider */}
          <div className="w-px h-6 mx-1" style={{ background: `${activeMode.color}20` }} />
        </div>

        {/* ── Mode switcher ──────────────────────────────────────── */}
        <div
          className="flex items-center rounded-md p-0.5 gap-px shrink-0"
          style={{
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.07)',
          }}
        >
          {MODES.map(({ id, label, icon: Icon, color, dimColor }) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className="relative flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[10px] font-bold tracking-widest font-mono transition-all duration-300"
              style={{
                color: mode === id ? color : 'rgba(255,255,255,0.35)',
              }}
            >
              {mode === id && (
                <motion.div
                  layoutId="active-mode-bg"
                  className="absolute inset-0 rounded"
                  style={{
                    background: dimColor,
                    border: `1px solid ${color}35`,
                    boxShadow: `inset 0 0 12px ${color}08`,
                  }}
                  transition={{ type: 'spring', stiffness: 420, damping: 32 }}
                />
              )}
              <Icon size={11} className="relative z-10 shrink-0" />
              <span className="relative z-10 hidden sm:inline">{label}</span>
            </button>
          ))}
        </div>

        {/* ── System status ─────────────────────────────────────── */}
        <div className="hidden md:flex items-center gap-1.5 shrink-0 pl-1">
          <Radio size={10} style={{ color: dataLoading ? '#fbbf24' : '#34d399' }} />
          <span
            className="text-[9px] font-mono font-bold tracking-widest"
            style={{ color: dataLoading ? '#fbbf24' : '#34d399' }}
          >
            {dataLoading ? 'SYNC' : 'LIVE'}
          </span>
        </div>

        {/* ── Market ticker (flex fill) ──────────────────────────── */}
        <div className="flex-1 overflow-hidden mx-1 hidden md:block min-w-0">
          <MarketTicker accentColor={activeMode.color} />
        </div>

        {/* ── UTC Clock ─────────────────────────────────────────── */}
        <div className="hidden lg:flex flex-col items-end shrink-0 mr-1">
          <span
            className="text-[12px] font-mono font-bold tabular-nums leading-none"
            style={{
              color: activeMode.color,
              textShadow: `0 0 8px ${activeMode.color}60`,
            }}
          >
            {utcTime}
          </span>
          <span className="text-[8px] font-mono text-foreground/30 tracking-widest leading-none mt-0.5">
            {utcDate} · UTC
          </span>
        </div>

        {/* ── Right panel toggle ─────────────────────────────────── */}
        <button
          onClick={toggleRightPanel}
          className="flex items-center justify-center w-7 h-7 rounded shrink-0 transition-all duration-200 hover:bg-white/10"
          style={{ color: `${activeMode.color}80` }}
          title="Toggle right panel"
        >
          <PanelRightClose size={15} />
        </button>
      </div>
    </motion.div>
  );
};
