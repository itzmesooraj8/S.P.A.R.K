/**
 * MapContainer — Full-bleed 3D globe using deck.gl + MapLibre.
 * Renders ScatterplotLayer (events) and ArcLayer (connections) per active mode.
 * Supports cinematic flyTo transitions triggered via Zustand store.
 */
import { useCallback, useMemo } from 'react';
import { Map } from 'react-map-gl/maplibre';
import { DeckGL } from '@deck.gl/react';
import { ScatterplotLayer, ArcLayer } from '@deck.gl/layers';
import { FlyToInterpolator } from '@deck.gl/core';
import 'maplibre-gl/dist/maplibre-gl.css';
import { useMonitorStore } from '@/store/useMonitorStore';
import { getEventsForMode, getArcsForMode } from '@/data/mockData';

/** Severity → RGBA color mapping for scatterplot points */
const SEVERITY_COLORS: Record<string, [number, number, number, number]> = {
  low: [0, 200, 150, 180],
  medium: [255, 180, 0, 200],
  high: [255, 120, 0, 220],
  critical: [255, 30, 50, 255],
};

/** Mode → arc color schemes */
const ARC_COLORS: Record<string, { source: [number, number, number, number]; target: [number, number, number, number] }> = {
  world: { source: [0, 220, 255, 180], target: [0, 220, 255, 40] },
  tech: { source: [0, 200, 255, 180], target: [140, 80, 255, 40] },
  finance: { source: [255, 200, 0, 180], target: [255, 200, 0, 40] },
  happy: { source: [0, 200, 120, 180], target: [0, 200, 120, 40] },
};

const MAP_STYLE = 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json';

export const MapContainer = () => {
  const mode = useMonitorStore((s) => s.mode);
  const viewState = useMonitorStore((s) => s.viewState);
  const setViewState = useMonitorStore((s) => s.setViewState);

  const events = useMemo(() => getEventsForMode(mode), [mode]);
  const arcs = useMemo(() => getArcsForMode(mode), [mode]);
  const arcColors = ARC_COLORS[mode];

  /** deck.gl visualization layers */
  const layers = useMemo(
    () => [
      new ScatterplotLayer({
        id: 'events-scatter',
        data: events,
        getPosition: (d: any) => [d.lng, d.lat],
        getRadius: (d: any) => {
          const sizes: Record<string, number> = { critical: 80000, high: 60000, medium: 40000, low: 25000 };
          return sizes[d.severity] ?? 30000;
        },
        getFillColor: (d: any) => SEVERITY_COLORS[d.severity] ?? [100, 100, 100, 150],
        radiusMinPixels: 4,
        radiusMaxPixels: 25,
        opacity: 0.8,
        pickable: true,
        autoHighlight: true,
        highlightColor: [0, 220, 255, 100],
        transitions: { getPosition: 800, getRadius: 800, getFillColor: 800 },
      }),
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
    ],
    [events, arcs, arcColors]
  );

  /** Handle interactive view state changes (pan/zoom/tilt) */
  const onViewStateChange = useCallback(
    ({ viewState: vs }: any) => {
      setViewState(vs);
    },
    [setViewState]
  );

  /** Apply FlyToInterpolator when a transition is requested */
  const effectiveViewState = useMemo(() => {
    if (viewState.transitionDuration > 0) {
      return {
        ...viewState,
        transitionInterpolator: new FlyToInterpolator({ curve: 1.414 }),
        transitionEasing: (t: number) => 1 - Math.pow(1 - t, 3), // ease-out cubic
      };
    }
    return viewState;
  }, [viewState]);

  return (
    <div className="absolute inset-0">
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
