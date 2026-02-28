/**
 * MapContainer — Full-bleed 3D globe using deck.gl + MapLibre.
 * Layers rendered in order:
 *   1. Arc connections (mock curated by mode)
 *   2. Conflict / earthquake scatter (merged real + mock fallback)
 *   3. NASA EONET wildfire scatter (red/orange dots)
 *   4. Climate anomaly scatter (teal dots, storms/volcanoes/floods)
 */
import { useCallback, useMemo } from 'react';
import { Map } from 'react-map-gl/maplibre';
import { DeckGL } from '@deck.gl/react';
import { ScatterplotLayer, ArcLayer } from '@deck.gl/layers';
import { FlyToInterpolator } from '@deck.gl/core';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useMonitorStore } from '@/store/useMonitorStore';
import { getEventsForMode, getArcsForMode } from '@/data/mockData';

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

// CartoDB dark-matter-nolabels — pure black base, geography in dark charcoal
const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-nolabels-gl-style/style.json';

export const MapContainer = () => {
  const mode = useMonitorStore((s) => s.mode);
  const viewState = useMonitorStore((s) => s.viewState);
  const setViewState = useMonitorStore((s) => s.setViewState);

  // Real-time data
  const realWorldEvents = useMonitorStore((s) => s.realWorldEvents);
  const realEvents = useMonitorStore((s) => s.realEvents);     // earthquakes + flights
  const realFireEvents = useMonitorStore((s) => s.realFireEvents);
  const realClimateEvents = useMonitorStore((s) => s.realClimateEvents);
  const lastFetch = useMonitorStore((s) => s.lastFetch);

  // Merge mock events with real events
  const events = useMemo(() => {
    const mockEvs = getEventsForMode(mode);
    if (lastFetch === 0) return mockEvs;
    // Combine real world events + earthquakes/flights with mock as baseline
    const realCombined = [...realWorldEvents, ...realEvents];
    const seen = new Set(realCombined.map((e) => e.id));
    const extras = mockEvs.filter((e) => !seen.has(e.id));
    return [...realCombined, ...extras];
  }, [mode, realWorldEvents, realEvents, lastFetch]);

  const arcs = useMemo(() => getArcsForMode(mode), [mode]);
  const arcColors = ARC_COLORS[mode];

  const layers = useMemo(
    () => [
      // Arc connections
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

      // Main events scatter (conflict + earthquakes + flights)
      new ScatterplotLayer({
        id: 'events-scatter',
        data: events,
        getPosition: (d: any) => [d.lng, d.lat],
        getRadius: (d: any) => {
          const sizes: Record<string, number> = { critical: 80000, high: 60000, medium: 40000, low: 25000 };
          return sizes[(d.severity) ?? 'medium'] ?? 30000;
        },
        getFillColor: (d: any) => SEVERITY_COLORS[(d.severity) ?? 'medium'] ?? [100, 100, 100, 150],
        radiusMinPixels: 4,
        radiusMaxPixels: 25,
        opacity: 0.8,
        pickable: true,
        autoHighlight: true,
        highlightColor: [0, 220, 255, 100],
        transitions: { getPosition: 800, getRadius: 800, getFillColor: 800 },
      }),

      // Wildfire scatter (NASA EONET) — bright orange/red flame dots
      new ScatterplotLayer({
        id: 'wildfire-scatter',
        data: realFireEvents,
        getPosition: (d: any) => [d.lng, d.lat],
        getRadius: 35000,
        getFillColor: [255, 80, 0, 220],
        radiusMinPixels: 3,
        radiusMaxPixels: 15,
        opacity: 0.9,
        pickable: true,
        autoHighlight: true,
        highlightColor: [255, 200, 0, 120],
      }),

      // Climate anomaly scatter (NASA EONET) — teal/cyan dots for storms/volcanoes/floods
      new ScatterplotLayer({
        id: 'climate-scatter',
        data: realClimateEvents,
        getPosition: (d: any) => [d.lng, d.lat],
        getRadius: (d: any) => {
          const sizes: Record<string, number> = { critical: 70000, high: 50000, medium: 35000, low: 20000 };
          return sizes[(d.severity)] ?? 30000;
        },
        getFillColor: (d: any) => {
          const cat = d.category || '';
          if (cat === 'volcanoes') return [255, 60, 20, 230] as [number, number, number, number];
          if (cat === 'severeStorms') return [0, 180, 255, 200] as [number, number, number, number];
          if (cat === 'floods') return [30, 120, 255, 200] as [number, number, number, number];
          return [0, 200, 200, 180] as [number, number, number, number];
        },
        radiusMinPixels: 3,
        radiusMaxPixels: 20,
        opacity: 0.8,
        pickable: true,
        autoHighlight: true,
        highlightColor: [0, 255, 200, 100],
      }),
    ],
    [events, arcs, arcColors, realFireEvents, realClimateEvents],
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
        viewState={effectiveViewState}
        onViewStateChange={onViewStateChange}
        controller={true}
        layers={layers}
        getCursor={() => 'default'}
      >
        <Map mapStyle={MAP_STYLE} attributionControl={false} />
      </DeckGL>
    </div>
  );
};



