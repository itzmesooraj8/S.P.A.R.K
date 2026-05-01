/**
 * MapControls — floating HUD control for map view/style/labels.
 * Renders as a compact pill-bar near the top-right of the globe.
 * Stores state in Zustand (persisted across navigation).
 */
import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Globe2, Map, Satellite, Navigation, Tag, EyeOff, SlidersHorizontal } from 'lucide-react';
import { useMonitorStore } from '@/store/useMonitorStore';

const MAP_STYLE_OPTS = [
  { id: 'dark',      label: 'Dark',      icon: Globe2,    desc: 'Carto Dark Matter' },
  { id: 'street',    label: 'Street',    icon: Map,       desc: 'Carto Voyager' },
  { id: 'satellite', label: 'Satellite', icon: Satellite, desc: 'ESRI World Imagery' },
] as const;

type Props = { accentColor?: string };

export const MapControls: React.FC<Props> = ({ accentColor = '#00f5ff' }) => {
  const mapView   = useMonitorStore((s) => s.mapView);
  const mapStyle  = useMonitorStore((s) => s.mapStyle);
  const mapLabels = useMonitorStore((s) => s.mapLabels);
  const setMapView   = useMonitorStore((s) => s.setMapView);
  const setMapStyle  = useMonitorStore((s) => s.setMapStyle);
  const setMapLabels = useMonitorStore((s) => s.setMapLabels);
  const [open, setOpen] = useState(false);

  return (
    <div className="relative pointer-events-auto">
      {/* Trigger button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-mono font-semibold
                   border transition-all duration-200 tracking-wider"
        style={{
          color: open ? accentColor : `${accentColor}90`,
          background: open ? `${accentColor}10` : 'rgba(255,255,255,0.03)',
          borderColor: open ? `${accentColor}50` : 'rgba(255,255,255,0.08)',
          boxShadow: open ? `0 0 12px ${accentColor}18` : 'none',
        }}
        title="Map Controls"
      >
        <SlidersHorizontal size={12} />
        <span className="hidden sm:inline">MAP</span>
        <span className="text-[10px] opacity-60 hidden sm:inline">
          {mapView.toUpperCase()} · {mapStyle.toUpperCase()} {mapLabels ? '· LBL' : ''}
        </span>
      </button>

      {/* Popover */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -6, scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 360, damping: 28 }}
            className="absolute top-full right-0 mt-2 z-50 w-56 rounded-xl overflow-hidden"
            style={{
              background: 'rgba(4, 10, 22, 0.97)',
              border: `1px solid ${accentColor}20`,
              boxShadow: `0 8px 40px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.03)`,
              backdropFilter: 'blur(24px)',
            }}
          >
            {/* View toggle */}
            <div className="px-3 pt-3 pb-2">
              <p className="text-[9px] font-mono tracking-[0.25em] text-gray-500 uppercase mb-2">
                Projection
              </p>
              <div className="grid grid-cols-2 gap-1">
                {(['2d', '3d'] as const).map((v) => (
                  <button
                    key={v}
                    onClick={() => setMapView(v)}
                    className="py-1.5 rounded-lg text-xs font-bold font-mono tracking-widest transition-all duration-200"
                    style={{
                      background: mapView === v ? `${accentColor}18` : 'rgba(255,255,255,0.03)',
                      color: mapView === v ? accentColor : 'rgba(255,255,255,0.40)',
                      border: `1px solid ${mapView === v ? `${accentColor}45` : 'rgba(255,255,255,0.06)'}`,
                      boxShadow: mapView === v ? `inset 0 0 8px ${accentColor}10` : 'none',
                    }}
                  >
                    {v === '2d' ? '⊟ 2D FLAT' : '🌐 3D GLOBE'}
                  </button>
                ))}
              </div>
            </div>

            {/* Divider */}
            <div className="h-px mx-3" style={{ background: `${accentColor}12` }} />

            {/* Style selector */}
            <div className="px-3 py-2">
              <p className="text-[9px] font-mono tracking-[0.25em] text-gray-500 uppercase mb-2">
                Base style
              </p>
              <div className="space-y-1">
                {MAP_STYLE_OPTS.map(({ id, label, icon: Icon, desc }) => (
                  <button
                    key={id}
                    onClick={() => setMapStyle(id)}
                    className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-xs transition-all duration-150"
                    style={{
                      background: mapStyle === id ? `${accentColor}14` : 'transparent',
                      color: mapStyle === id ? accentColor : 'rgba(255,255,255,0.50)',
                      border: `1px solid ${mapStyle === id ? `${accentColor}40` : 'transparent'}`,
                    }}
                  >
                    <Icon size={13} className="shrink-0" />
                    <span className="font-semibold tracking-wide">{label}</span>
                    <span className="ml-auto text-[10px] opacity-50">{desc}</span>
                    {mapStyle === id && (
                      <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: accentColor }} />
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Divider */}
            <div className="h-px mx-3" style={{ background: `${accentColor}12` }} />

            {/* Labels toggle */}
            <div className="px-3 py-2 pb-3">
              <button
                onClick={() => setMapLabels(!mapLabels)}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-xs transition-all duration-150"
                style={{
                  background: mapLabels ? `${accentColor}14` : 'rgba(255,255,255,0.03)',
                  color: mapLabels ? accentColor : 'rgba(255,255,255,0.40)',
                  border: `1px solid ${mapLabels ? `${accentColor}40` : 'rgba(255,255,255,0.06)'}`,
                }}
              >
                {mapLabels ? <Tag size={13} /> : <EyeOff size={13} />}
                <span className="font-semibold tracking-wide">Country Labels</span>
                <span
                  className="ml-auto text-[10px] font-bold tracking-widest"
                  style={{ color: mapLabels ? accentColor : '#6b7280' }}
                >
                  {mapLabels ? 'ON' : 'OFF'}
                </span>
              </button>
              {mapStyle === 'satellite' && (
                <p className="text-[9px] text-gray-500 mt-1.5 text-center">
                  Satellite imagery: no key required (ESRI)
                </p>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Click-away backdrop */}
      {open && (
        <div className="fixed inset-0 z-40" onClick={() => setOpen(false)} />
      )}
    </div>
  );
};
