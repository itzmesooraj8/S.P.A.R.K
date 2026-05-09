import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AiStatus } from '@/hooks/useVoiceEngine';

interface Props {
  status: AiStatus;
  isListening: boolean;
  amplitude: number[];
  aiMode: string;
  onToggleMic: () => void;
}

const STATUS_CONFIG: Record<string, { color: string; label: string }> = {
  idle:        { color: '#00E5FF', label: 'IDLE' },
  listening:   { color: '#00FF88', label: 'LISTENING' },
  thinking:    { color: '#FFB800', label: 'PROCESSING' },
  responding:  { color: '#0088FF', label: 'RESPONDING' },
  combat:      { color: '#FF3B5C', label: 'COMBAT' },
  degraded:    { color: '#FF9F0A', label: 'DEGRADED' },
};

export default function AICore({ status, isListening, amplitude, aiMode, onToggleMic }: Props) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.idle;
  
  // Calculate energy from amplitude
  const avgAmp = amplitude.length > 0 
    ? amplitude.reduce((sum, val) => sum + val, 0) / amplitude.length 
    : 0;
  
  // Smooth energy transition
  const [energy, setEnergy] = useState(0);
  useEffect(() => {
    setEnergy(prev => prev + (avgAmp - prev) * 0.2); // Smooth lerp
  }, [avgAmp]);

  // Framer variants for the core
  const coreVariants = {
    idle: { scale: [1, 1.02, 1], transition: { duration: 4, repeat: Infinity, ease: 'easeInOut' } },
    listening: { scale: [1, 1.05, 1], transition: { duration: 2, repeat: Infinity, ease: 'easeInOut' } },
    thinking: { scale: [1, 1.1, 1], rotate: [0, 180, 360], transition: { duration: 1.5, repeat: Infinity, ease: 'linear' } },
    responding: { scale: 1 + energy * 0.5, transition: { type: 'spring', damping: 15, stiffness: 200 } }
  };

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center">
      {/* Dynamic ambient glow */}
      <motion.div 
        animate={{ 
          background: `radial-gradient(circle, ${cfg.color}33 0%, transparent 60%)`,
          scale: 1 + energy * 0.3
        }}
        transition={{ duration: 0.3 }}
        className="absolute inset-0 pointer-events-none"
      />
      
      {/* Orb Container */}
      <div className="relative w-72 h-72 flex items-center justify-center cursor-pointer group" onClick={onToggleMic}>
        
        {/* Ring 1 - Slow Outer */}
        <motion.div 
          animate={{ rotate: 360 }} 
          transition={{ duration: 30, repeat: Infinity, ease: "linear" }}
          className="absolute inset-0 rounded-full border border-dashed opacity-30"
          style={{ borderColor: cfg.color, borderWidth: '1px' }}
        />
        
        {/* Ring 2 - Medium Inner Reverse */}
        <motion.div 
          animate={{ rotate: -360 }} 
          transition={{ duration: 20, repeat: Infinity, ease: "linear" }}
          className="absolute inset-4 rounded-full border opacity-40"
          style={{ 
            borderColor: cfg.color, 
            borderWidth: '1px', 
            borderLeftColor: 'transparent',
            borderRightColor: 'transparent'
          }}
        />

        {/* Core Animated Orb */}
        <motion.div
          variants={coreVariants}
          animate={status}
          className="relative w-32 h-32 rounded-full flex items-center justify-center shadow-2xl backdrop-blur-md"
          style={{
            background: `radial-gradient(circle at 30% 30%, ${cfg.color}88, ${cfg.color}22 70%, transparent)`,
            boxShadow: `0 0 ${40 + energy * 60}px ${cfg.color}66, inset 0 0 20px ${cfg.color}44`,
            border: `1px solid ${cfg.color}66`
          }}
        >
          {/* Inner core bright spot */}
          <motion.div 
            animate={{ scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] }}
            transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }}
            className="w-12 h-12 rounded-full"
            style={{ 
              background: cfg.color,
              filter: 'blur(8px)',
              opacity: 0.8 + energy * 0.2
            }}
          />
        </motion.div>

        {/* Audio Reactive Particles (simplistic approach using SVG dots) */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100">
          {Array.from({ length: 12 }).map((_, i) => {
            const angle = (i * 30 * Math.PI) / 180;
            const r = 35 + (amplitude[i % amplitude.length] || 0) * 15;
            const x = 50 + r * Math.cos(angle);
            const y = 50 + r * Math.sin(angle);
            return (
              <motion.circle 
                key={i}
                cx={x} cy={y} r={1.5}
                fill={cfg.color}
                animate={{ cx: x, cy: y }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                style={{ opacity: 0.5 + energy }}
              />
            );
          })}
        </svg>

      </div>

      {/* Status Text & Telemetry */}
      <div className="absolute bottom-10 flex flex-col items-center">
        <motion.div 
          key={status}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          className="font-space text-sm tracking-[0.3em] font-bold"
          style={{ color: cfg.color, textShadow: `0 0 10px ${cfg.color}` }}
        >
          {cfg.label}
        </motion.div>
        
        <div className="font-mono-tech text-[10px] text-white/40 mt-1 uppercase tracking-widest">
          SYS.{aiMode}.CORE // {isListening ? 'MIC_ACTIVE' : 'STANDBY'}
        </div>
      </div>
    </div>
  );
}
