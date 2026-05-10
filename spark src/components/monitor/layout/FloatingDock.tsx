import { Layers2, Eye, BookOpen, Keyboard } from 'lucide-react';
import { CombatDock } from '../../combat/CombatDock';

export function DockButton({
  icon, label, active, accentColor, onClick,
}: {
  icon: React.ReactNode;
  label: string;
  active: boolean;
  accentColor: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-2 pl-2.5 pr-3 py-1.5 rounded-lg text-[10px] font-mono
                 font-bold tracking-widest transition-all duration-200 group"
      style={{
        background: active ? `${accentColor}18` : 'rgba(2,8,20,0.82)',
        border: `1px solid ${active ? `${accentColor}45` : 'rgba(255,255,255,0.09)'}`,
        color: active ? accentColor : 'rgba(255,255,255,0.45)',
        backdropFilter: 'blur(16px)',
        boxShadow: active ? `0 0 14px ${accentColor}22` : '0 2px 12px rgba(0,0,0,0.3)',
      }}
      title={label}
    >
      <span style={{ color: active ? accentColor : 'rgba(255,255,255,0.4)' }}>{icon}</span>
      <span>{label}</span>
    </button>
  );
}

interface FloatingDockProps {
  layerPanelOpen: boolean;
  setLayerPanelOpen: React.Dispatch<React.SetStateAction<boolean>>;
  streetViewMode: boolean;
  setStreetViewMode: React.Dispatch<React.SetStateAction<boolean>>;
  setStreetViewCoords: React.Dispatch<React.SetStateAction<any>>;
  caseDrawerOpen: boolean;
  toggleCaseDrawer: () => void;
  cmdOpen: boolean;
  setCmdOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setCombatModalOpen: React.Dispatch<React.SetStateAction<boolean>>;
  accentColor: string;
}

export function FloatingDock({
  layerPanelOpen, setLayerPanelOpen,
  streetViewMode, setStreetViewMode, setStreetViewCoords,
  caseDrawerOpen, toggleCaseDrawer,
  cmdOpen, setCmdOpen,
  setCombatModalOpen,
  accentColor
}: FloatingDockProps) {
  return (
    <div
      className="fixed bottom-9 right-3 z-50 pointer-events-auto flex-col gap-1.5 items-end hidden md:flex"
    >
      <DockButton
        icon={<Layers2 size={14} />}
        label="Layers"
        active={layerPanelOpen}
        accentColor={accentColor}
        onClick={() => setLayerPanelOpen((v) => !v)}
      />
      <DockButton
        icon={<Eye size={14} />}
        label="Street View"
        active={streetViewMode}
        accentColor={accentColor}
        onClick={() => {
          setStreetViewMode((v) => !v);
          if (streetViewMode) setStreetViewCoords(null);
        }}
      />
      <DockButton
        icon={<BookOpen size={14} />}
        label="Cases"
        active={caseDrawerOpen}
        accentColor={accentColor}
        onClick={toggleCaseDrawer}
      />
      <DockButton
        icon={<Keyboard size={14} />}
        label="⌃K"
        active={cmdOpen}
        accentColor={accentColor}
        onClick={() => setCmdOpen(true)}
      />
      <CombatDock onOpenModal={() => setCombatModalOpen(true)} />
    </div>
  );
}
