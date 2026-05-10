import { motion, AnimatePresence } from 'framer-motion';
import { BarChart3, HeartPulse, Archive } from 'lucide-react';
import { InstabilityIndex } from '../InstabilityIndex';
import { FusionPanel } from '../FusionPanel';
import RuntimeOrchestratorPanel from '../RuntimeOrchestratorPanel';
import RuntimeArchitecturePanel from '../RuntimeArchitecturePanel';
import ProviderHealthPanel from '../ProviderHealthPanel';
import { SnapshotPlayback } from '../SnapshotPlayback';
import { PanelTabs } from './PanelTabs';
import { PanelShell } from './PanelShell';

export const RIGHT_TABS = [
  { id: 'signal',  label: 'SIGNAL',  icon: BarChart3 },
  { id: 'health',  label: 'HEALTH',  icon: HeartPulse },
  { id: 'archive', label: 'ARCHIVE', icon: Archive },
] as const;

export type RightTab = typeof RIGHT_TABS[number]['id'];

interface RightPanelProps {
  open: boolean;
  tab: RightTab;
  onTabChange: (tab: RightTab) => void;
  accentColor: string;
  modeColors: Record<string, string>;
  hudMode: string;
}

export function RightPanel({ open, tab, onTabChange, accentColor, modeColors, hudMode }: RightPanelProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="right-panel"
          initial={{ opacity: 0, x: 48, scale: 0.96 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: 40, scale: 0.96 }}
          transition={{ type: 'spring', stiffness: 300, damping: 28 }}
          className="pointer-events-auto hidden md:flex flex-col shrink-0"
          style={{ width: '18rem', height: '100%' }}
        >
          <PanelShell accentColor={accentColor} width="18rem">
            <PanelTabs tabs={RIGHT_TABS} active={tab} onSelect={onTabChange as any} accentColor={accentColor} />

            <div className="flex-1 overflow-y-auto scrollbar-hud">
              <AnimatePresence mode="wait">
                {tab === 'signal' && (
                  <motion.div key="signal" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                    <InstabilityIndex accentColor={accentColor} />
                    <FusionPanel accentColor={modeColors.tech} />
                  </motion.div>
                )}
                {tab === 'health' && (
                  <motion.div key="health" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                    {hudMode === 'developer' ? (
                      <>
                        <RuntimeOrchestratorPanel accentColor={accentColor} />
                        <RuntimeArchitecturePanel accentColor={accentColor} />
                      </>
                    ) : (
                      <div className="rounded-2xl border border-white/8 bg-black/28 backdrop-blur-xl px-3 py-3 text-white/65">
                        <div className="text-[9px] uppercase tracking-[0.35em] text-cyan-100/65 font-orbitron">Focused Health</div>
                        <div className="mt-2 text-[11px] leading-relaxed text-white/72 font-rajdhani">
                          Developer mode reveals the runtime graph and orchestrator stream. Normal mode stays on provider health and signal quality.
                        </div>
                      </div>
                    )}
                    <ProviderHealthPanel accentColor={accentColor} />
                  </motion.div>
                )}
                {tab === 'archive' && (
                  <motion.div key="archive" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                    <SnapshotPlayback accentColor={accentColor} mode="inline" />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </PanelShell>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
