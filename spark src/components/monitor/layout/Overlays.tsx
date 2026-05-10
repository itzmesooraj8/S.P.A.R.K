import { AnimatePresence, motion } from 'framer-motion';
import { LayerTogglePanel } from '../LayerTogglePanel';
import { CaseDrawer } from '../CaseDrawer';
import { CommandPalette } from '../CommandPalette';
import { StreetViewPanel, type StreetViewCoords } from '../StreetViewPanel';
import { CombatModeModal } from '../../combat/CombatModeModal';
import { ReconPanel } from '../../combat/ReconPanel';
import { SigintPanel } from '../../combat/SigintPanel';
import { TorGateway } from '../../combat/TorGateway';
import { VaultPanel } from '../../combat/VaultPanel';

interface OverlaysProps {
  layerPanelOpen: boolean;
  setLayerPanelOpen: (open: boolean) => void;
  caseDrawerOpen: boolean;
  cmdOpen: boolean;
  setCmdOpen: (open: boolean) => void;
  streetViewMode: boolean;
  setStreetViewMode: (open: boolean) => void;
  streetViewCoords: StreetViewCoords | null;
  setStreetViewCoords: (coords: StreetViewCoords | null) => void;
  combatModalOpen: boolean;
  setCombatModalOpen: (open: boolean) => void;
  combatActivePanel: string | null;
  accentColor: string;
}

export function Overlays({
  layerPanelOpen, setLayerPanelOpen,
  caseDrawerOpen,
  cmdOpen, setCmdOpen,
  streetViewMode, setStreetViewMode,
  streetViewCoords, setStreetViewCoords,
  combatModalOpen, setCombatModalOpen,
  combatActivePanel,
  accentColor
}: OverlaysProps) {
  return (
    <>
      <LayerTogglePanel open={layerPanelOpen} onClose={() => setLayerPanelOpen(false)} />
      <CaseDrawer accentColor={accentColor} />
      <CommandPalette open={cmdOpen} onOpenChange={setCmdOpen} accentColor={accentColor} />

      {/* Street View panel — shown when streetViewMode is active and coords picked */}
      {streetViewMode && (
        <StreetViewPanel
          coords={streetViewCoords}
          onClose={() => { setStreetViewMode(false); setStreetViewCoords(null); }}
          accentColor={accentColor}
        />
      )}
      {streetViewMode && !streetViewCoords && (
        <div
          className="fixed bottom-10 left-1/2 -translate-x-1/2 z-50 px-4 py-2 rounded-full text-[10px] font-mono font-bold tracking-widest pointer-events-none"
          style={{ background: `${accentColor}20`, border: `1px solid ${accentColor}50`, color: accentColor }}
        >
          STREET VIEW ACTIVE — CLICK ANY LOCATION ON THE GLOBE
        </div>
      )}

      {/* ══ Combat Mode Modal ═══════════════════════════════════ */}
      <CombatModeModal open={combatModalOpen} onClose={() => setCombatModalOpen(false)} />

      {/* ══ Combat Panels ═══════════════════════════════════════ */}
      <AnimatePresence>
        {(combatActivePanel === 'identity' || combatActivePanel === 'recon') && (
          <motion.div
            key="combat-recon"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="fixed left-4 z-50 pointer-events-auto"
            style={{ top: '60px', maxHeight: 'calc(100vh - 80px)', overflowY: 'auto' }}
          >
            <ReconPanel />
          </motion.div>
        )}
        {combatActivePanel === 'sigint' && (
          <motion.div
            key="combat-sigint"
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            className="fixed left-4 z-50 pointer-events-auto"
            style={{ top: '60px', maxHeight: 'calc(100vh - 80px)', overflowY: 'auto' }}
          >
            <SigintPanel />
          </motion.div>
        )}
        {combatActivePanel === 'tor' && (
          <motion.div
            key="combat-tor"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="fixed right-16 z-50 pointer-events-auto"
            style={{ top: '60px', maxHeight: 'calc(100vh - 80px)', overflowY: 'auto' }}
          >
            <TorGateway />
          </motion.div>
        )}
        {combatActivePanel === 'vault' && (
          <motion.div
            key="combat-vault"
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="fixed right-16 z-50 pointer-events-auto"
            style={{ top: '60px', maxHeight: 'calc(100vh - 80px)', overflowY: 'auto' }}
          >
            <VaultPanel />
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
