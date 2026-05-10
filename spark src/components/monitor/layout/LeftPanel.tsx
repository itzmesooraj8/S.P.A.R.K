import { motion, AnimatePresence } from 'framer-motion';
import { ChevronLeft, AlertTriangle, Newspaper, Settings2 } from 'lucide-react';
import { ThreatMatrix } from '../ThreatMatrix';
import { LiveNewsPanel } from '../LiveNewsPanel';
import { GdeltIntelPanel } from '../GdeltIntelPanel';
import { CustomMonitorPanel } from '../CustomMonitorPanel';
import { ClimateAnomalyPanel } from '../ClimateAnomalyPanel';
import { PanelTabs } from './PanelTabs';
import { PanelShell } from './PanelShell';

export const LEFT_TABS = [
  { id: 'threats', label: 'THREATS', icon: AlertTriangle },
  { id: 'intel',   label: 'INTEL',   icon: Newspaper },
  { id: 'monitor', label: 'MONITOR', icon: Settings2 },
] as const;

export type LeftTab = typeof LEFT_TABS[number]['id'];

interface LeftPanelProps {
  open: boolean;
  tab: LeftTab;
  onTabChange: (tab: LeftTab) => void;
  accentColor: string;
  onToggle: () => void;
}

export function LeftPanel({ open, tab, onTabChange, accentColor, onToggle }: LeftPanelProps) {
  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="left-panel"
          initial={{ opacity: 0, x: -48, scale: 0.96 }}
          animate={{ opacity: 1, x: 0, scale: 1 }}
          exit={{ opacity: 0, x: -40, scale: 0.96 }}
          transition={{ type: 'spring', stiffness: 300, damping: 28 }}
          className="pointer-events-auto hidden md:flex flex-col shrink-0 group"
          style={{ width: '19rem', height: '100%' }}
        >
          <PanelShell accentColor={accentColor} width="19rem">
            {/* Tab bar */}
            <PanelTabs tabs={LEFT_TABS} active={tab} onSelect={onTabChange as any} accentColor={accentColor} />

            {/* Tab content */}
            <div className="flex-1 overflow-y-auto scrollbar-hud">
              <AnimatePresence mode="wait">
                {tab === 'threats' && (
                  <motion.div key="threats" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                    <ThreatMatrix accentColor={accentColor} />
                  </motion.div>
                )}
                {tab === 'intel' && (
                  <motion.div key="intel" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                    <LiveNewsPanel accentColor={accentColor} />
                    <GdeltIntelPanel accentColor={accentColor} />
                  </motion.div>
                )}
                {tab === 'monitor' && (
                  <motion.div key="monitor" initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }} className="p-2 flex flex-col gap-2">
                    <CustomMonitorPanel accentColor={accentColor} />
                    <ClimateAnomalyPanel accentColor={accentColor} />
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </PanelShell>

          {/* Collapse handle */}
          <button
            onClick={onToggle}
            className="absolute -right-3 top-1/2 -translate-y-1/2 w-5 h-10 rounded-r-md flex items-center justify-center
                       opacity-0 group-hover:opacity-100 transition-opacity pointer-events-auto"
            style={{ background: `${accentColor}20`, border: `1px solid ${accentColor}30`, color: accentColor }}
          >
            <ChevronLeft size={12} />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
