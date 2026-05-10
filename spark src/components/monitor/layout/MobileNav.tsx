import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, BarChart3 } from 'lucide-react';
import { ThreatMatrix } from '../ThreatMatrix';
import { LiveNewsPanel } from '../LiveNewsPanel';
import { GdeltIntelPanel } from '../GdeltIntelPanel';
import { CustomMonitorPanel } from '../CustomMonitorPanel';
import RuntimeOrchestratorPanel from '../RuntimeOrchestratorPanel';
import RuntimeArchitecturePanel from '../RuntimeArchitecturePanel';
import { InstabilityIndex } from '../InstabilityIndex';
import { FusionPanel } from '../FusionPanel';
import ProviderHealthPanel from '../ProviderHealthPanel';

interface MobileNavProps {
  mobileTab: 'left' | 'right' | null;
  setMobileTab: (tab: 'left' | 'right' | null) => void;
  accentColor: string;
  modeColors: Record<string, string>;
  hudMode: string;
}

export function MobileNav({ mobileTab, setMobileTab, accentColor, modeColors, hudMode }: MobileNavProps) {
  return (
    <>
      <div
        className="fixed bottom-0 left-0 right-0 z-50 flex md:hidden items-center"
        style={{
          background: 'rgba(1,8,20,0.97)',
          borderTop: `1px solid ${accentColor}20`,
          backdropFilter: 'blur(20px)',
          height: '52px',
        }}
      >
        {[
          { id: 'left' as const,  label: 'THREATS', icon: AlertTriangle },
          { id: null,             label: 'MAP',      icon: null },
          { id: 'right' as const, label: 'SIGNAL',   icon: BarChart3 },
        ].map(({ id, label, icon: Icon }) => (
          <button
            key={label}
            onClick={() => setMobileTab(mobileTab === id ? null : id)}
            className="flex-1 flex flex-col items-center justify-center gap-1 text-[9px] font-mono
                       font-bold tracking-widest transition-colors duration-200"
            style={{ color: mobileTab === id ? accentColor : 'rgba(255,255,255,0.3)' }}
          >
            {Icon ? <Icon size={16} /> : (
              <div className="w-4 h-4 rounded-full border" style={{ borderColor: mobileTab === id ? accentColor : 'rgba(255,255,255,0.2)', background: mobileTab === id ? `${accentColor}20` : 'transparent' }} />
            )}
            {label}
          </button>
        ))}
      </div>

      <AnimatePresence>
        {mobileTab && (
          <motion.div
            key={`mobile-${mobileTab}`}
            initial={{ y: '100%' }}
            animate={{ y: 0 }}
            exit={{ y: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className="fixed bottom-[52px] left-0 right-0 z-40 md:hidden rounded-t-2xl overflow-hidden"
            style={{
              height: '60vh',
              background: 'rgba(2,8,20,0.97)',
              border: `1px solid ${accentColor}20`,
              backdropFilter: 'blur(28px)',
            }}
          >
            <div className="h-full overflow-y-auto scrollbar-hud p-3 flex flex-col gap-2">
              {mobileTab === 'left' && (
                <>
                  <ThreatMatrix accentColor={accentColor} />
                  <LiveNewsPanel accentColor={accentColor} />
                  <GdeltIntelPanel accentColor={accentColor} />
                  <CustomMonitorPanel accentColor={accentColor} />
                </>
              )}
              {mobileTab === 'right' && (
                <>
                  {hudMode === 'developer' ? (
                    <>
                      <RuntimeOrchestratorPanel accentColor={accentColor} />
                      <RuntimeArchitecturePanel accentColor={accentColor} />
                    </>
                  ) : (
                    <div className="rounded-2xl border border-white/8 bg-black/28 backdrop-blur-xl px-3 py-3 text-white/70">
                      <div className="text-[9px] uppercase tracking-[0.35em] text-cyan-100/65 font-orbitron">Runtime Hidden</div>
                      <div className="mt-1 text-[11px] leading-relaxed text-white/65 font-rajdhani">Switch to developer mode to expose the orchestration feed.</div>
                    </div>
                  )}
                  <InstabilityIndex accentColor={accentColor} />
                  <FusionPanel accentColor={modeColors.tech} />
                  <ProviderHealthPanel accentColor={accentColor} />
                </>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
