/**
 * StreetViewPanel — Embedded Google Maps Street View for a picked coordinate.
 *
 * When streetViewMode is active, clicking the globe sets coords here.
 * Panel attempts an iframe embed; also provides a direct "Open in Google Maps" link.
 */
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, ExternalLink, MapPin, Navigation } from 'lucide-react';

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
  if (!coords) return null;

  const { lat, lng, label } = coords;
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
              background: '#34d399',
              boxShadow: '0 0 6px #34d39960',
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

        {/* Static map preview + action buttons (iframe blocked by X-Frame-Options) */}
        <div className="relative flex-1 overflow-hidden flex flex-col items-center justify-center gap-4 px-6">
          {/* OpenStreetMap static tile preview */}
          <div className="w-full rounded overflow-hidden border" style={{ borderColor: `${accentColor}20` }}>
            <img
              src={`https://staticmap.openstreetmap.de/staticmap.php?center=${lat},${lng}&zoom=15&size=380x220&maptype=mapnik&markers=${lat},${lng},lightblue`}
              alt={`Map at ${coordStr}`}
              className="w-full h-auto"
              style={{ minHeight: 140 }}
              onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
            />
          </div>

          <div className="text-center">
            <MapPin size={28} style={{ color: `${accentColor}80` }} className="mx-auto mb-2" />
            <p className="text-[11px] font-mono text-gray-300 mb-1">Street-level imagery</p>
            <p className="text-[9px] font-mono text-gray-500">Open in an external viewer below</p>
          </div>

          <div className="flex flex-col gap-2 w-full">
            <a
              href={mapsLink}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 py-2.5 rounded-lg text-[10px] font-mono font-bold
                         tracking-widest transition-all duration-200 hover:opacity-90"
              style={{
                background: `${accentColor}20`,
                border: `1px solid ${accentColor}45`,
                color: accentColor,
              }}
            >
              <ExternalLink size={12} />
              OPEN GOOGLE STREET VIEW
            </a>
            <a
              href={mapillaryLink}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 py-2.5 rounded-lg text-[10px] font-mono font-bold
                         tracking-widest transition-all duration-200 hover:opacity-90"
              style={{
                background: 'rgba(255,255,255,0.04)',
                border: '1px solid rgba(255,255,255,0.12)',
                color: 'rgba(255,255,255,0.5)',
              }}
            >
              <ExternalLink size={12} />
              OPEN MAPILLARY
            </a>
          </div>
        </div>

        {/* Footer: coordinates */}
        <div
          className="flex items-center justify-center px-3 py-2 shrink-0"
          style={{ borderTop: `1px solid ${accentColor}14` }}
        >
          <span className="text-[9px] font-mono text-gray-500">{coordStr}</span>
        </div>
      </motion.div>
    </AnimatePresence>
  );
};
