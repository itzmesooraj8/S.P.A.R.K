/**
 * BasePanel — SPARK HUD glassmorphic panel wrapper.
 * Features:
 *   - Dynamic accent color per panel (cyan / amber / green / purple)
 *   - Corner bracket decorations (military HUD aesthetic)
 *   - Top + bottom accent glow lines
 *   - Smooth collapse / expand via Framer Motion
 */
import { useState, type ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown } from 'lucide-react';

interface BasePanelProps {
  title: string;
  icon?: ReactNode;
  badge?: ReactNode;
  children: ReactNode;
  className?: string;
  defaultCollapsed?: boolean;
  /** CSS color string used for accent lines & corner brackets */
  accentColor?: string;
}

export const BasePanel = ({
  title,
  icon,
  badge,
  children,
  className = '',
  defaultCollapsed = false,
  accentColor = 'hsl(186 100% 50%)',
}: BasePanelProps) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <motion.div
      className={`panel-hud relative ${className}`}
      initial={{ opacity: 0, y: 10, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: 8, scale: 0.97 }}
      transition={{ type: 'spring', stiffness: 280, damping: 30 }}
      layout
    >
      {/* ── Corner bracket decorations ─────────────────────────── */}
      <span className="corner-tl" style={{ color: accentColor }} />
      <span className="corner-tr" style={{ color: accentColor }} />
      <span className="corner-bl" style={{ color: accentColor }} />
      <span className="corner-br" style={{ color: accentColor }} />

      {/* ── Top accent line ─────────────────────────────────────── */}
      <div
        className="h-px w-full"
        style={{
          background: `linear-gradient(90deg, transparent 0%, ${accentColor} 35%, ${accentColor} 65%, transparent 100%)`,
          opacity: 0.85,
        }}
      />

      {/* ── Header ──────────────────────────────────────────────── */}
      <div
        className="flex items-center gap-2 px-3 py-2.5 cursor-pointer select-none transition-colors duration-150"
        style={{ background: 'transparent' }}
        onClick={() => setCollapsed(!collapsed)}
        onMouseEnter={(e) => ((e.currentTarget as HTMLDivElement).style.background = 'rgba(255,255,255,0.025)')}
        onMouseLeave={(e) => ((e.currentTarget as HTMLDivElement).style.background = 'transparent')}
      >
        {/* Icon with accent background ring */}
        {icon && (
          <div
            className="flex items-center justify-center w-5 h-5 rounded shrink-0"
            style={{
              background: `color-mix(in srgb, ${accentColor} 10%, transparent)`,
              border: `1px solid color-mix(in srgb, ${accentColor} 30%, transparent)`,
            }}
          >
            {icon}
          </div>
        )}

        {/* Title */}
        <span className="text-[10px] font-bold tracking-[0.2em] uppercase font-mono text-foreground/70 flex-1 truncate">
          {title}
        </span>

        {/* Status badge */}
        {badge}

        {/* Collapse/expand chevron */}
        <motion.div
          animate={{ rotate: collapsed ? 0 : 180 }}
          transition={{ duration: 0.2, ease: 'easeInOut' }}
          className="shrink-0"
          style={{ color: `color-mix(in srgb, ${accentColor} 70%, transparent)` }}
        >
          <ChevronDown size={13} />
        </motion.div>
      </div>

      {/* ── Collapsible body ─────────────────────────────────────── */}
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            <div
              className="border-t"
              style={{ borderColor: `color-mix(in srgb, ${accentColor} 15%, transparent)` }}
            >
              {children}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── Bottom dim accent ────────────────────────────────────── */}
      <div
        className="h-px w-full"
        style={{
          background: `linear-gradient(90deg, transparent 0%, ${accentColor} 35%, ${accentColor} 65%, transparent 100%)`,
          opacity: 0.15,
        }}
      />
    </motion.div>
  );
};
