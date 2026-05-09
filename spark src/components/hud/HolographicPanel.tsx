import React, { ReactNode } from 'react';
import { motion } from 'framer-motion';

interface Props {
  children: ReactNode;
  className?: string;
  title?: string;
  glowColor?: string;
  delay?: number;
}

export default function HolographicPanel({ 
  children, 
  className = '', 
  title, 
  glowColor = '#00E5FF',
  delay = 0
}: Props) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay, ease: 'easeOut' }}
      className={`relative rounded-xl overflow-hidden ${className}`}
      style={{
        background: 'rgba(5, 15, 25, 0.45)',
        backdropFilter: 'blur(14px)',
        border: `1px solid ${glowColor}20`,
        boxShadow: `0 0 20px ${glowColor}15, inset 0 0 20px rgba(255,255,255,0.03)`
      }}
    >
      {/* Corner Brackets */}
      <div className="absolute top-0 left-0 w-3 h-3 border-t-2 border-l-2 opacity-50" style={{ borderColor: glowColor }} />
      <div className="absolute top-0 right-0 w-3 h-3 border-t-2 border-r-2 opacity-50" style={{ borderColor: glowColor }} />
      <div className="absolute bottom-0 left-0 w-3 h-3 border-b-2 border-l-2 opacity-50" style={{ borderColor: glowColor }} />
      <div className="absolute bottom-0 right-0 w-3 h-3 border-b-2 border-r-2 opacity-50" style={{ borderColor: glowColor }} />

      {/* Title Bar */}
      {title && (
        <div className="flex items-center px-4 py-2 border-b" style={{ borderColor: `${glowColor}20`, background: `linear-gradient(90deg, ${glowColor}10, transparent)` }}>
          <span className="font-space text-[10px] uppercase tracking-widest font-bold" style={{ color: glowColor }}>
            {title}
          </span>
          <div className="ml-auto flex gap-1">
            <div className="w-1 h-1 rounded-full bg-white/20" />
            <div className="w-1 h-1 rounded-full bg-white/20" />
            <div className="w-1 h-1 rounded-full bg-white/20" />
          </div>
        </div>
      )}

      {/* Content */}
      <div className="p-4 relative z-10 h-full">
        {children}
      </div>

      {/* Animated Scanline Overlay */}
      <div className="absolute inset-0 pointer-events-none opacity-[0.03] z-20"
        style={{
          background: 'repeating-linear-gradient(0deg, transparent, transparent 2px, #fff 2px, #fff 4px)'
        }}
      />
      <motion.div 
        animate={{ y: ['-100%', '200%'] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'linear' }}
        className="absolute inset-x-0 h-10 z-20 pointer-events-none"
        style={{ background: `linear-gradient(180deg, transparent, ${glowColor}20, transparent)` }}
      />
    </motion.div>
  );
}
