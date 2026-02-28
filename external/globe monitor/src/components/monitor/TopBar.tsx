/**
 * TopBar — Floating top HUD bar.
 * Contains mode switcher tabs, system status, and live market ticker.
 */
import { Globe, Cpu, TrendingUp, Heart, PanelLeftClose, PanelRightClose } from 'lucide-react';
import { motion } from 'framer-motion';
import { useMonitorStore, type MonitorMode } from '@/store/useMonitorStore';
import { MarketTicker } from './MarketTicker';

const modes: { id: MonitorMode; label: string; icon: typeof Globe }[] = [
  { id: 'world', label: 'WORLD', icon: Globe },
  { id: 'tech', label: 'TECH', icon: Cpu },
  { id: 'finance', label: 'FINANCE', icon: TrendingUp },
  { id: 'happy', label: 'HAPPY', icon: Heart },
];

export const TopBar = () => {
  const mode = useMonitorStore((s) => s.mode);
  const setMode = useMonitorStore((s) => s.setMode);
  const toggleLeftPanel = useMonitorStore((s) => s.toggleLeftPanel);
  const toggleRightPanel = useMonitorStore((s) => s.toggleRightPanel);

  return (
    <motion.div
      className="fixed top-0 left-0 right-0 z-50 glass-panel-strong"
      initial={{ y: -80 }}
      animate={{ y: 0 }}
      transition={{ type: 'spring', stiffness: 200, damping: 30 }}
    >
      <div className="flex items-center h-12 px-3 gap-3">
        {/* Left panel toggle */}
        <button
          onClick={toggleLeftPanel}
          className="text-muted-foreground hover:text-primary transition-colors hidden md:block"
        >
          <PanelLeftClose size={16} />
        </button>

        {/* Mode switcher with animated background pill */}
        <div className="flex items-center gap-0.5 bg-background/50 rounded-lg p-0.5">
          {modes.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              onClick={() => setMode(id)}
              className={`relative flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-300 ${
                mode === id
                  ? 'text-primary-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {mode === id && (
                <motion.div
                  layoutId="mode-indicator"
                  className="absolute inset-0 bg-primary rounded-md"
                  transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                />
              )}
              <Icon size={13} className="relative z-10" />
              <span className="relative z-10 hidden sm:inline font-mono tracking-wider">
                {label}
              </span>
            </button>
          ))}
        </div>

        {/* System status */}
        <div className="hidden lg:flex items-center gap-2 shrink-0">
          <span className="text-[10px] font-bold tracking-[0.2em] text-primary neon-glow-cyan font-mono">
            WORLD MONITOR V2
          </span>
          <span className="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse" />
          <span className="text-[9px] text-neon-green font-mono font-semibold">LIVE</span>
        </div>

        {/* Ticker fills remaining space */}
        <div className="flex-1 overflow-hidden mx-2">
          <MarketTicker />
        </div>

        {/* Right panel toggle */}
        <button
          onClick={toggleRightPanel}
          className="text-muted-foreground hover:text-primary transition-colors hidden md:block"
        >
          <PanelRightClose size={16} />
        </button>
      </div>
    </motion.div>
  );
};
