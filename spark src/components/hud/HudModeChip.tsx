import { Layers3 } from 'lucide-react';

type Props = {
  mode: 'normal' | 'developer';
  onToggle: () => void;
  compact?: boolean;
};

export default function HudModeChip({ mode, onToggle, compact = false }: Props) {
  const active = mode === 'developer';

  return (
    <button
      onClick={onToggle}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 transition-all duration-200 ${compact ? 'text-[8px]' : 'text-[9px]'}`}
      style={{
        borderColor: active ? 'rgba(0,245,255,0.35)' : 'rgba(255,255,255,0.14)',
        background: active ? 'rgba(0,245,255,0.09)' : 'rgba(255,255,255,0.03)',
        color: active ? '#dffcff' : 'rgba(255,255,255,0.72)',
        boxShadow: active ? '0 0 24px rgba(0,245,255,0.08)' : 'none',
      }}
      title="Toggle HUD mode (Ctrl+Shift+O)"
    >
      <Layers3 size={10} />
      <span className="font-orbitron tracking-[0.35em] uppercase">{active ? 'DEV MODE' : 'NORMAL MODE'}</span>
      <span className="font-mono-tech opacity-60">Ctrl+Shift+O</span>
    </button>
  );
}
