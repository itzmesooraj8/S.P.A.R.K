/**
 * useUrlState — Shareable URL state for SPARK Globe Monitor.
 * Encodes/decodes: map center+zoom, mode, time window, visible layers.
 *
 * Format (URL hash): #lng,lat,zoom,mode,timeWindow,layers
 * Example: #20.0,25.0,2.2,world,24h,conflict+earthquake+wildfire
 *
 * Usage: Call once at mount in GlobeMonitor.tsx — it both reads the initial
 * URL state into the store AND subscribes to store changes to keep URL in sync.
 */
import { useEffect, useRef } from 'react';
import { useMonitorStore, type MonitorMode, type TimeWindow, type LayerId, ALL_LAYERS } from '@/store/useMonitorStore';

const VALID_MODES = new Set<MonitorMode>(['world', 'tech', 'finance', 'happy']);
const VALID_WINDOWS = new Set<TimeWindow>(['1h', '6h', '24h', '48h', '7d']);
const VALID_LAYERS = new Set<string>(ALL_LAYERS);

function encodeHash(
  lng: number,
  lat: number,
  zoom: number,
  mode: MonitorMode,
  timeWindow: TimeWindow,
  visibleLayers: LayerId[],
): string {
  const layers = visibleLayers.join('+');
  return `#${lng.toFixed(2)},${lat.toFixed(2)},${zoom.toFixed(1)},${mode},${timeWindow},${layers}`;
}

function decodeHash(hash: string): {
  lng: number; lat: number; zoom: number;
  mode: MonitorMode; timeWindow: TimeWindow;
  visibleLayers: LayerId[];
} | null {
  try {
    const raw = hash.replace('#', '');
    const parts = raw.split(',');
    if (parts.length < 6) return null;
    const [lngS, latS, zoomS, modeS, twS, layersS] = parts;
    const lng   = parseFloat(lngS);
    const lat   = parseFloat(latS);
    const zoom  = parseFloat(zoomS);
    if (isNaN(lng) || isNaN(lat) || isNaN(zoom)) return null;
    const mode       = VALID_MODES.has(modeS as MonitorMode) ? (modeS as MonitorMode) : 'world';
    const timeWindow = VALID_WINDOWS.has(twS as TimeWindow) ? (twS as TimeWindow) : '24h';
    const visibleLayers = (layersS || '')
      .split('+')
      .filter((l) => VALID_LAYERS.has(l)) as LayerId[];
    return { lng, lat, zoom, mode, timeWindow, visibleLayers };
  } catch {
    return null;
  }
}

export function useUrlState() {
  const setMode         = useMonitorStore((s) => s.setMode);
  const setTimeWindow   = useMonitorStore((s) => s.setTimeWindow);
  const setVisibleLayers = useMonitorStore((s) => s.setVisibleLayers);
  const setViewState    = useMonitorStore((s) => s.setViewState);
  const isWriting = useRef(false); // prevent feedback loops

  // ── Read hash on mount ────────────────────────────────────────────────────
  useEffect(() => {
    const hash = window.location.hash;
    if (hash && hash.length > 1) {
      const parsed = decodeHash(hash);
      if (parsed) {
        isWriting.current = true;
        setViewState({
          longitude: parsed.lng,
          latitude:  parsed.lat,
          zoom:      parsed.zoom,
          pitch:     35,
          bearing:   0,
          transitionDuration: 0,
        });
        setMode(parsed.mode);
        setTimeWindow(parsed.timeWindow);
        if (parsed.visibleLayers.length > 0) {
          setVisibleLayers(parsed.visibleLayers);
        }
        setTimeout(() => { isWriting.current = false; }, 200);
      }
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Write hash on store change ────────────────────────────────────────────
  useEffect(() => {
    const unsubscribe = useMonitorStore.subscribe(
      (s) => ({
        lng:           s.viewState.longitude,
        lat:           s.viewState.latitude,
        zoom:          s.viewState.zoom,
        mode:          s.mode,
        timeWindow:    s.timeWindow,
        visibleLayers: s.visibleLayers,
      }),
      ({ lng, lat, zoom, mode, timeWindow, visibleLayers }) => {
        if (isWriting.current) return;
        const newHash = encodeHash(lng, lat, zoom, mode, timeWindow, visibleLayers);
        if (window.location.hash !== newHash) {
          window.history.replaceState(null, '', newHash);
        }
      },
      { equalityFn: (a, b) =>
          a.lng === b.lng && a.lat === b.lat && a.zoom === b.zoom &&
          a.mode === b.mode && a.timeWindow === b.timeWindow &&
          a.visibleLayers.join() === b.visibleLayers.join()
      }
    );
    return unsubscribe;
  }, []);

  // Return a shareable URL for the current state
  const getShareUrl = () => {
    const s = useMonitorStore.getState();
    const hash = encodeHash(
      s.viewState.longitude,
      s.viewState.latitude,
      s.viewState.zoom,
      s.mode,
      s.timeWindow,
      s.visibleLayers,
    );
    return `${window.location.origin}${window.location.pathname}${hash}`;
  };

  return { getShareUrl };
}
