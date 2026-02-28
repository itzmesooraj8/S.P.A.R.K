/**
 * StreetViewPanel — Embedded Google Maps Street View for a picked coordinate.
 *
 * When streetViewMode is active, clicking the globe sets coords here.
 * Panel attempts an iframe embed; also provides a direct "Open in Google Maps" link.
 */
import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, MapPin, Navigation, RefreshCw } from 'lucide-react';

export interface StreetViewCoords {
  lat: number;
  lng: number;
  label?: string;
}

interface Props {
  coords: StreetViewCoords | null;
  onClose: () => void;
  accentColor?: string;
}

/** Build a Google Maps street-view embed URL (no API key needed for basic embed) */
function buildStreetViewUrl(lat: number, lng: number) {
  // This URL opens the Google Maps viewer centered on the street-view panorama
  return `https://www.google.com/maps?q=&layer=c&cbll=${lat},${lng}&cbp=11,0,0,0,0&output=svembed`;
}

/** Google Maps street-view direct link (opens in new tab) */
function buildMapsLink(lat: number, lng: number) {
  return `https://www.google.com/maps/@${lat},${lng},3a,75y,90t/data=!3m6!1e1`;
}

/** Mapillary street-level imagery link */
function buildMapillaryLink(lat: number, lng: number) {
  return `https://www.mapillary.com/app/?lat=${lat}&lng=${lng}&z=16`;
}

export const StreetViewPanel: React.FC<Props> = ({
  coords, onClose, accentColor = '#00f5ff',
}) => {
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const [loadState, setLoadState] = useState<'loading' | 'loaded' | 'error'>('loading');

  useEffect(() => {
    if (coords) setLoadState('loading');
  }, [coords?.lat, coords?.lng]);

  if (!coords) return null;

  const { lat, lng, label } = coords;
  const svUrl       = buildStreetViewUrl(lat, lng);
  const mapsLink    = buildMapsLink(lat, lng);
  const mapillaryLink = buildMapillaryLink(lat, lng);
  const coordStr    = `${Math.abs(lat).toFixed(4)}°${lat >= 0 ? 'N' : 'S'}, ${Math.abs(lng).toFixed(4)}°${lng >= 0 ? 'E' : 'W'}`;

  return (
    <AnimatePresence>
      <motion.div
        key="sv-panel"
        initial={{ opacity: 0, x: 40, scale: 0.97 }}
        animate={{ opacity: 1, x: 0, scale: 1 }}
        exit={{ opacity: 0, x: 32, scale: 0.97 }}
        transition={{ type: 'spring', stiffness: 320, damping: 30 }}
        className="fixed top-14 right-0 z-50 flex flex-col overflow-hidden"
        style={{
          width: '400px',
          height: 'calc(100vh - 82px)',
          background: 'rgba(2, 8, 20, 0.97)',
          border: `1px solid ${accentColor}28`,
          borderRight: 'none',
          boxShadow: `0 0 60px rgba(0,0,0,0.6), -4px 0 20px rgba(0,0,0,0.4)`,
          backdropFilter: 'blur(32px)',
        }}
      >
        {/* Header */}
        <div
          className="flex items-center gap-2 px-3 py-2 shrink-0"
          style={{
            borderBottom: `1px solid ${accentColor}18`,
            background: `${accentColor}06`,
          }}
        >
          <Navigation size={13} style={{ color: accentColor }} />
          <div className="flex flex-col min-w-0 flex-1">
            <span
              className="text-[10px] font-mono font-bold tracking-[0.2em] uppercase truncate"
              style={{ color: accentColor }}
            >
              {label ?? 'STREET VIEW'}
            </span>
            <span className="text-[9px] font-mono text-gray-500 tracking-wider">{coordStr}</span>
          </div>
          {/* Status dot */}
          <span
            className="w-1.5 h-1.5 rounded-full shrink-0"
            style={{
              background: loadState === 'loaded' ? '#34d399' : loadState === 'error' ? '#f87171' : '#fbbf24',
              boxShadow: loadState === 'loaded' ? '0 0 6px #34d39960' : 'none',
            }}
          />
          <button
            onClick={onClose}
            className="w-6 h-6 flex items-center justify-center rounded transition-colors hover:bg-white/10 shrink-0"
            style={{ color: 'rgba(255,255,255,0.4)' }}
          >
            <X size={12} />
          </button>
        </div>

        {/* Iframe embed */}
        <div className="relative flex-1 overflow-hidden">
          {loadState === 'loading' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 z-10"
              style={{ background: 'rgba(2,8,20,0.92)' }}>
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ duration: 1.2, repeat: Infinity, ease: 'linear' }}
              >
                <RefreshCw size={20} style={{ color: accentColor }} />
              </motion.div>
              <span className="text-[10px] font-mono text-gray-400 tracking-wider">LOADING STREET VIEW…</span>
            </div>
          )}

          {loadState === 'error' && (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-4 px-6">
              <MapPin size={32} style={{ color: `${accentColor}50` }} />
              <div className="text-center">
                <p className="text-[11px] font-mono text-gray-300 mb-1">Street view unavailable</p>
                <p className="text-[9px] font-mono text-gray-500">No street-level imagery at this location, or Google blocked the embed. Use the links below.</p>
              </div>
            </div>
          )}

          <iframe
            ref={iframeRef}
            src={svUrl}
            className="w-full h-full border-0"
            allow="fullscreen"
            onLoad={() => setLoadState('loaded')}
            onError={() => setLoadState('error')}
            title="Google Maps Street View"
            sandbox="allow-scripts allow-same-origin allow-popups"
          />
        </div>

        {/* Footer actions */}
        <div
          className="flex items-center gap-2 px-3 py-2 shrink-0"
          style={{ borderTop: `1px solid ${accentColor}14` }}
        >
          <a
            href={mapsLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex-1 flex items-center justify-center gap-1.5 py-2 rounded-lg text-[10px] font-mono font-bold
                       tracking-widest transition-all duration-200 hover:opacity-90"
            style={{
              background: `${accentColor}20`,
              border: `1px solid ${accentColor}45`,
              color: accentColor,
            }}
          >
            <ExternalLink size={11} />
            OPEN IN GOOGLE MAPS
          </a>
          <a
            href={mapillaryLink}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-[10px] font-mono font-bold
                       tracking-widest transition-all duration-200 hover:opacity-90"
            style={{
              background: 'rgba(255,255,255,0.04)',
              border: '1px solid rgba(255,255,255,0.12)',
              color: 'rgba(255,255,255,0.5)',
            }}
            title="Open in Mapillary (free street-level imagery)"
          >
            <ExternalLink size={11} />
            MAPILLARY
          </a>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
