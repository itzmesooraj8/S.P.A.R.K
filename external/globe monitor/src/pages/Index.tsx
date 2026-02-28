/**
 * Index — Main layout for World Monitor V2.
 * Full-bleed HUD with floating glassmorphic panels over a 3D globe.
 * Mouse-tracking parallax effect on all floating panels.
 */
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useMonitorStore } from '@/store/useMonitorStore';
import { MapContainer } from '@/components/monitor/MapContainer';
import { TopBar } from '@/components/monitor/TopBar';
import { ThreatMatrix } from '@/components/monitor/ThreatMatrix';
import { InstabilityIndex } from '@/components/monitor/InstabilityIndex';
import { AICore } from '@/components/monitor/AICore';

const Index = () => {
  const leftPanelOpen = useMonitorStore((s) => s.leftPanelOpen);
  const rightPanelOpen = useMonitorStore((s) => s.rightPanelOpen);
  const mode = useMonitorStore((s) => s.mode);

  // Mouse position for parallax effect
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    const x = (e.clientX / window.innerWidth - 0.5) * 2;
    const y = (e.clientY / window.innerHeight - 0.5) * 2;
    setMousePos({ x, y });
  }, []);

  return (
    <div
      className="h-screen w-screen overflow-hidden starfield"
      onMouseMove={handleMouseMove}
    >
      {/* Base layer: 3D Globe */}
      <MapContainer />

      {/* Atmosphere glow overlay */}
      <div className="absolute inset-0 atmosphere-glow" />

      {/* Top Bar: mode switcher + ticker */}
      <TopBar />

      {/* Floating side panels with mouse parallax */}
      <div className="fixed inset-0 pointer-events-none pt-14 pb-24 px-3 z-40">
        <div
          className="relative h-full flex gap-3 transition-transform duration-100 ease-out"
          style={{
            transform: `translate(${mousePos.x * 4}px, ${mousePos.y * 3}px)`,
          }}
        >
          {/* Left panel: Threat Matrix */}
          <AnimatePresence mode="wait">
            {leftPanelOpen && (
              <motion.div
                key={`left-${mode}`}
                initial={{ opacity: 0, x: -40, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: -40, scale: 0.95 }}
                transition={{ type: 'spring', stiffness: 250, damping: 28 }}
                className="pointer-events-auto w-80 hidden md:block"
              >
                <ThreatMatrix />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Center spacer */}
          <div className="flex-1" />

          {/* Right panel: Instability Index */}
          <AnimatePresence mode="wait">
            {rightPanelOpen && (
              <motion.div
                key="right-panel"
                initial={{ opacity: 0, x: 40, scale: 0.95 }}
                animate={{ opacity: 1, x: 0, scale: 1 }}
                exit={{ opacity: 0, x: 40, scale: 0.95 }}
                transition={{ type: 'spring', stiffness: 250, damping: 28 }}
                className="pointer-events-auto w-72 hidden md:block"
              >
                <InstabilityIndex />
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* AI Core: bottom center */}
      <AICore />
    </div>
  );
};

export default Index;
