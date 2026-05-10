import { motion } from 'framer-motion';

export function PanelTabs<T extends string>({
  tabs, active, onSelect, accentColor,
}: {
  tabs: readonly { id: T; label: string; icon: React.ComponentType<{ size?: number }> }[];
  active: T;
  onSelect: (id: T) => void;
  accentColor: string;
}) {
  return (
    <div
      className="flex items-center gap-px shrink-0"
      style={{
        background: 'rgba(255,255,255,0.025)',
        borderBottom: `1px solid rgba(255,255,255,0.06)`,
      }}
    >
      {tabs.map(({ id, label, icon: Icon }) => (
        <button
          key={id}
          onClick={() => onSelect(id)}
          className="relative flex-1 flex items-center justify-center gap-1.5 py-2 text-[9px] font-bold
                     tracking-[0.18em] font-mono transition-colors duration-200"
          style={{ color: active === id ? accentColor : 'rgba(255,255,255,0.3)' }}
        >
          {active === id && (
            <motion.div
              layoutId={`tab-bg-${tabs[0].id}`}
              className="absolute inset-0"
              style={{ background: `${accentColor}10`, borderBottom: `2px solid ${accentColor}` }}
              transition={{ type: 'spring', stiffness: 400, damping: 32 }}
            />
          )}
          <Icon size={10} className="relative z-10 shrink-0" />
          <span className="relative z-10">{label}</span>
        </button>
      ))}
    </div>
  );
}
