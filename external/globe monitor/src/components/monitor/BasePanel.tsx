/**
 * BasePanel — Glassmorphic wrapper for all floating HUD panels.
 * Supports collapse/expand with Framer Motion animation.
 */
import { useState, type ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronUp, GripVertical } from 'lucide-react';

interface BasePanelProps {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
  defaultCollapsed?: boolean;
}

export const BasePanel = ({
  title,
  icon,
  children,
  className = '',
  defaultCollapsed = false,
}: BasePanelProps) => {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  return (
    <motion.div
      className={`glass-panel rounded-xl overflow-hidden ${className}`}
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      layout
    >
      {/* Panel header — click to collapse/expand */}
      <div
        className="flex items-center gap-2 px-3 py-2.5 border-b border-border/30 cursor-pointer select-none hover:bg-secondary/20 transition-colors"
        onClick={() => setCollapsed(!collapsed)}
      >
        <GripVertical size={12} className="text-muted-foreground/40" />
        {icon}
        <span className="text-[11px] font-semibold tracking-widest text-muted-foreground uppercase font-mono flex-1">
          {title}
        </span>
        {collapsed ? (
          <ChevronDown size={14} className="text-muted-foreground" />
        ) : (
          <ChevronUp size={14} className="text-muted-foreground" />
        )}
      </div>

      {/* Collapsible content */}
      <AnimatePresence initial={false}>
        {!collapsed && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: 'easeInOut' }}
            className="overflow-hidden"
          >
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
