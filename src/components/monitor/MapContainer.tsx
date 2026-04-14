/**
 * MapContainer — Multi-mode globe/map for SPARK Globe Monitor.
 * Supports:
 *   View:   2D (flat) | 3D (deck.gl GlobeView + MapLibre globe projection)
 *   Style:  Dark | Street (Carto Voyager) | Satellite (ESRI World Imagery)
 *   Labels: Country + city names toggle
 */
import { useCallback, useMemo } from 'react';
import { Map } from 'react-map-gl/maplibre';
import { DeckGL } from '@deck.gl/react';
import { ScatterplotLayer, ArcLayer } from '@deck.gl/layers';
import { FlyToInterpolator, _GlobeView as GlobeView, MapView } from '@deck.gl/core';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useMonitorStore, TIME_WINDOW_MS } from '@/store/useMonitorStore';
import { getEventsForMode, getArcsForMode } from '@/data/monitorSeed';

// ── Map style URLs ────────────────────────────────────────────────────────────
const STYLES = {
  dark:         'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json',
  darkLabels:   'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
  streetLabels: 'https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json',
};

/** Satellite GL style using free ESRI World Imagery tiles (no key needed) */
function buildSatelliteStyle(labels: boolean): object {
  return {
    version: 8,
    glyphs: 'https://fonts.openmaptiles.org/{fontstack}/{range}.pbf',
    sources: {
      esri: {
        type: 'raster',
        tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
        tileSize: 256,
        maxzoom: 19,
        attribution: '&copy; Esri &mdash; Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP',
      },
      ...(labels ? {
        osm_labels: {
          type: 'raster',
          tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
          tileSize: 256,
          maxzoom: 19,
        },
      } : {}),
    },
    layers: [
      { id: 'bg', type: 'background', paint: { 'background-color': '#010812' } },
      { id: 'satellite', type: 'raster', source: 'esri',
        paint: { 'raster-saturation': -0.05, 'raster-contrast': 0.1 } },
    ],
  };
}

// ── Severity and arc colors ───────────────────────────────────────────────────
const SEVERITY_COLORS: Record<string, [number, number, number, number]> = {
  low:      [0, 200, 150, 180],
  medium:   [255, 180, 0, 200],
  high:     [255, 120, 0, 220],
  critical: [255, 30, 50, 255],
};

const ARC_COLORS: Record<string, { source: [number, number, number, number]; target: [number, number, number, number] }> = {
  world:   { source: [0, 220, 255, 180], target: [0, 220, 255, 40] },
  tech:    { source: [0, 200, 255, 180], target: [140, 80, 255, 40] },
  finance: { source: [255, 200, 0, 180], target: [255, 200, 0, 40] },
  happy:   { source: [0, 200, 120, 180], target: [0, 200, 120, 40] },
};

export const MapContainer = ({ onMapClick }: { onMapClick?: (loc: { lat: number; lng: number }) => void } = {}) => {
  const mode            = useMonitorStore((s) => s.mode);
  const viewState       = useMonitorStore((s) => s.viewState);
  const setViewState    = useMonitorStore((s) => s.setViewState);
  const visibleLayers   = useMonitorStore((s) => s.visibleLayers);
  const timeWindow      = useMonitorStore((s) => s.timeWindow);
  const customMonitors  = useMonitorStore((s) => s.customMonitors);
  const mapView         = useMonitorStore((s) => s.mapView);
  const mapStyle        = useMonitorStore((s) => s.mapStyle);
  const mapLabels       = useMonitorStore((s) => s.mapLabels);
  const selectEvent     = useMonitorStore((s) => s.selectEvent);
  const flyTo           = useMonitorStore((s) => s.flyTo);

  const realWorldEvents   = useMonitorStore((s) => s.realWorldEvents);
  const realEvents        = useMonitorStore((s) => s.realEvents);
  const realFireEvents    = useMonitorStore((s) => s.realFireEvents);
  const realClimateEvents = useMonitorStore((s) => s.realClimateEvents);
  const newsGeoEvents     = useMonitorStore((s) => s.newsGeoEvents);
  const lastFetch         = useMonitorStore((s) => s.lastFetch);

  const zoom = viewState.zoom;

  // ── Resolved map style ──────────────────────────────────────────────────
  const resolvedStyle = useMemo(() => {
    if (mapStyle === 'satellite') return buildSatelliteStyle(mapLabels);
    if (mapStyle === 'street')   return STYLES.streetLabels;   // voyager always has labels
    return mapLabels ? STYLES.darkLabels : STYLES.dark;
  }, [mapStyle, mapLabels]);

  // ── deck.gl view (3D = GlobeView, 2D = MapView) ─────────────────────────
  const deckView = useMemo(
    () => mapView === '3d' ? new GlobeView({ id: 'globe' } as any) : new MapView({ id: 'map', repeat: true }),
    [mapView],
  );

  // ── Zoom-adaptive radius ────────────────────────────────────────────────
  const zoomScale = useMemo(() => {
    const t = Math.min(1, Math.max(0, (zoom - 1) / 11));
    return 2.0 - t * 1.7;
  }, [zoom]);

  // ── Time window filter ──────────────────────────────────────────────────
  const cutoff = useMemo(() => {
    if (lastFetch === 0) return 0;
    return Date.now() - TIME_WINDOW_MS[timeWindow];
  }, [timeWindow, lastFetch]);

  const withinWindow = useCallback(
    (fetchedAt?: number) => !fetchedAt || fetchedAt >= cutoff,
    [cutoff],
  );

  // ── Merge mock + real events ────────────────────────────────────────────
  const events = useMemo(() => {
    const mockEvs = getEventsForMode(mode);
    if (lastFetch === 0) return mockEvs;
    const realCombined = [...realWorldEvents, ...realEvents].filter((e) => withinWindow(e.fetchedAt));
    const seen = new Set(realCombined.map((e) => e.id));
    const extras = mockEvs.filter((e) => !seen.has(e.id));
    return [...realCombined, ...extras];
  }, [mode, realWorldEvents, realEvents, lastFetch, withinWindow]);

  const arcs      = useMemo(() => getArcsForMode(mode), [mode]);
  const arcColors = ARC_COLORS[mode];

  // ── Custom monitor color lookup ─────────────────────────────────────────
  const getCustomColor = useCallback(
    (title: string): [number, number, number, number] | null => {
      for (const m of customMonitors) {
        if (!m.enabled) continue;
        if (title.toLowerCase().includes(m.keyword)) {
          const hex = m.color.replace('#', '');
          const r = parseInt(hex.slice(0, 2), 16);
          const g = parseInt(hex.slice(2, 4), 16);
          const b = parseInt(hex.slice(4, 6), 16);
          return [r, g, b, 255];
        }
      }
      return null;
    },
    [customMonitors],
  );

  // ── Layers ──────────────────────────────────────────────────────────────
  const layers = useMemo(
    () => [
      new ArcLayer({
        id: 'connection-arcs',
        data: arcs,
        getSourcePosition: (d: any) => d.source,
        getTargetPosition: (d: any) => d.target,
        getSourceColor: arcColors.source,
        getTargetColor: arcColors.target,
        getWidth: 2,
        greatCircle: true,
      }),

      ...(visibleLayers.includes('conflict') || visibleLayers.includes('earthquake') || visibleLayers.includes('flights') ? [
        new ScatterplotLayer({
          id: 'events-scatter',
          data: events,
          getPosition: (d: any) => [d.lng, d.lat],
          getRadius: (d: any) => {
            const base: Record<string, number> = { critical: 80000, high: 60000, medium: 40000, low: 25000 };
            return (base[d.severity ?? 'medium'] ?? 30000) * zoomScale;
          },
          getFillColor: (d: any) => {
            const custom = getCustomColor(d.title || '');
            if (custom) return custom;
            return SEVERITY_COLORS[d.severity ?? 'medium'] ?? [100, 100, 100, 150];
          },
          radiusMinPixels: 3,
          radiusMaxPixels: Math.round(22 * zoomScale),
          opacity: 0.8, pickable: true, autoHighlight: true,
          highlightColor: [0, 220, 255, 100],
          transitions: { getPosition: 800, getRadius: 600, getFillColor: 800 },
          updateTriggers: { getFillColor: [customMonitors], getRadius: [zoomScale] },
        }),
      ] : []),

      ...(visibleLayers.includes('wildfire') ? [
        new ScatterplotLayer({
          id: 'wildfire-scatter',
          data: realFireEvents.filter((f) => withinWindow(f.fetchedAt)),
          getPosition: (d: any) => [d.lng, d.lat],
          getRadius: 35000 * zoomScale,
          getFillColor: [255, 80, 0, 220],
          radiusMinPixels: 2,
          radiusMaxPixels: Math.round(14 * zoomScale),
          opacity: 0.9, pickable: true, autoHighlight: true,
          highlightColor: [255, 200, 0, 120],
          updateTriggers: { getRadius: [zoomScale] },
        }),
      ] : []),

      ...(visibleLayers.includes('climate') ? [
        new ScatterplotLayer({
          id: 'climate-scatter',
          data: realClimateEvents.filter((e) => withinWindow(e.fetchedAt)),
          getPosition: (d: any) => [d.lng, d.lat],
          getRadius: (d: any) => {
            const sizes: Record<string, number> = { critical: 70000, high: 50000, medium: 35000, low: 20000 };
            return (sizes[d.severity] ?? 30000) * zoomScale;
          },
          getFillColor: (d: any) => {
            const cat = d.category || '';
            if (cat === 'volcanoes')    return [255, 60, 20, 230] as [number, number, number, number];
            if (cat === 'severeStorms') return [0, 180, 255, 200] as [number, number, number, number];
            if (cat === 'floods')       return [30, 120, 255, 200] as [number, number, number, number];
            return [0, 200, 200, 180] as [number, number, number, number];
          },
          radiusMinPixels: 3, radiusMaxPixels: Math.round(20 * zoomScale),
          opacity: 0.8, pickable: true, autoHighlight: true,
          highlightColor: [0, 255, 200, 100],
          updateTriggers: { getRadius: [zoomScale] },
        }),
      ] : []),

      ...(visibleLayers.includes('news') ? [
        new ScatterplotLayer({
          id: 'news-scatter',
          data: newsGeoEvents.filter((e) => withinWindow(e.fetchedAt)),
          getPosition: (d: any) => [d.lng, d.lat],
          getRadius: (d: any) => {
            const sizes: Record<string, number> = { critical: 65000, high: 45000, medium: 30000, low: 18000 };
            return (sizes[d.severity] ?? 25000) * zoomScale;
          },
          getFillColor: (d: any) => {
            // Blue-white spectrum by severity for news
            const sev = d.severity || 'medium';
            if (sev === 'critical') return [220, 80, 255, 230] as [number, number, number, number];
            if (sev === 'high')     return [120, 160, 255, 210] as [number, number, number, number];
            if (sev === 'medium')   return [80, 200, 255, 190] as [number, number, number, number];
            return [60, 230, 200, 160] as [number, number, number, number];
          },
          getLineColor: [255, 255, 255, 60],
          stroked: true,
          getLineWidth: 1,
          lineWidthMinPixels: 1,
          radiusMinPixels: 2,
          radiusMaxPixels: Math.round(16 * zoomScale),
          opacity: 0.75,
          pickable: true,
          autoHighlight: true,
          highlightColor: [255, 240, 80, 120],
          updateTriggers: { getRadius: [zoomScale] },
        }),
      ] : []),

      ...(visibleLayers.includes('custom') ? [
        new ScatterplotLayer({
          id: 'custom-monitor-glow',
          data: events.filter((e: any) => getCustomColor(e.title || '') !== null),
          getPosition: (d: any) => [d.lng, d.lat],
          getRadius: (d: any) => {
            const base: Record<string, number> = { critical: 110000, high: 90000, medium: 65000, low: 45000 };
            return (base[d.severity ?? 'medium'] ?? 70000) * zoomScale;
          },
          getFillColor: (d: any) => {
            const c = getCustomColor(d.title || '');
            return c ? [c[0], c[1], c[2], 40] as [number, number, number, number] : [0, 0, 0, 0];
          },
          getLineColor: (d: any) => {
            const c = getCustomColor(d.title || '');
            return c ? [c[0], c[1], c[2], 180] as [number, number, number, number] : [0, 0, 0, 0];
          },
          stroked: true, filled: true,
          getLineWidth: 2, lineWidthMinPixels: 1,
          radiusMinPixels: 5, radiusMaxPixels: 30,
          opacity: 0.9, pickable: false,
          updateTriggers: { getFillColor: [customMonitors], getLineColor: [customMonitors], getRadius: [zoomScale] },
        }),
      ] : []),
    ],
    [events, arcs, arcColors, realFireEvents, realClimateEvents, newsGeoEvents, visibleLayers, zoomScale, getCustomColor, withinWindow],
  );

  const onViewStateChange = useCallback(
    ({ viewState: vs }: any) => setViewState(vs),
    [setViewState],
  );

  const effectiveViewState = useMemo(() => {
    if (viewState.transitionDuration > 0) {
      return {
        ...viewState,
        transitionInterpolator: new FlyToInterpolator({ curve: 1.414 }),
        transitionEasing: (t: number) => 1 - Math.pow(1 - t, 3),
      };
    }
    return viewState;
  }, [viewState]);

  return (
    <div className="absolute inset-0" style={{ background: '#000' }}>
      <DeckGL
        views={deckView}
        viewState={effectiveViewState}
        onViewStateChange={onViewStateChange}
        controller={true}
        layers={layers}
        getCursor={() => 'default'}
        onClick={(info: any) => {
          if (info.object?.id) {
            selectEvent(info.object.id);
            const lng = info.object.lng ?? info.object.longitude ?? info.coordinate?.[0];
            const lat = info.object.lat ?? info.object.latitude ?? info.coordinate?.[1];
            if (lng != null && lat != null) flyTo(lng, lat, 6);
          } else if (!info.layer && info.coordinate) {
            onMapClick?.({ lat: info.coordinate[1], lng: info.coordinate[0] });
          }
        }}
      >
        <Map
          mapStyle={resolvedStyle as any}
          attributionControl={false}
          projection={mapView === '3d' ? ({ type: 'globe' } as any) : ({ type: 'mercator' } as any)}
        />
      </DeckGL>
    </div>
  );
};

