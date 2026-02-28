/**
 * CommandPalette — SPARK Ctrl+K command interface.
 * Allows quick navigation, map control, and layer management
 * via keyboard or click.
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  Command,
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
  CommandSeparator,
} from '@/components/ui/command';
import {
  Globe2, Map, Satellite, Layers, EyeOff, Eye,
  Navigation, Radio, Cpu, Tag,
} from 'lucide-react';
import { useMonitorStore, type ViewState } from '@/store/useMonitorStore';

/* World city fly-to presets */
const CITY_PRESETS = [
  { label: 'New York',     lat: 40.71, lng: -74.01 },
  { label: 'London',       lat: 51.51, lng: -0.13  },
  { label: 'Tokyo',        lat: 35.68, lng: 139.69 },
  { label: 'Dubai',        lat: 25.20, lng: 55.27  },
  { label: 'Singapore',    lat: 1.35,  lng: 103.82 },
  { label: 'Sydney',       lat: -33.87, lng: 151.21 },
  { label: 'São Paulo',    lat: -23.55, lng: -46.63 },
  { label: 'Lagos',        lat: 6.52,  lng: 3.38   },
  { label: 'Cairo',        lat: 30.04, lng: 31.24  },
  { label: 'Moscow',       lat: 55.75, lng: 37.62  },
  { label: 'Beijing',      lat: 39.91, lng: 116.39 },
  { label: 'Mumbai',       lat: 19.08, lng: 72.88  },
  { label: 'Los Angeles',  lat: 34.05, lng: -118.24 },
  { label: 'Paris',        lat: 48.86, lng: 2.35   },
  { label: 'Istanbul',     lat: 41.01, lng: 28.96  },
  { label: 'Nairobi',      lat: -1.29, lng: 36.82  },
  { label: 'Toronto',      lat: 43.65, lng: -79.38 },
  { label: 'Berlin',       lat: 52.52, lng: 13.40  },
  { label: 'Seoul',        lat: 37.57, lng: 126.98 },
  { label: 'Jakarta',      lat: -6.21, lng: 106.85 },
];

interface Props {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  accentColor?: string;
}

export const CommandPalette: React.FC<Props> = ({ open, onOpenChange, accentColor = '#00f5ff' }) => {
  const mapView      = useMonitorStore((s) => s.mapView);
  const mapStyle     = useMonitorStore((s) => s.mapStyle);
  const mapLabels    = useMonitorStore((s) => s.mapLabels);
  const setMapView   = useMonitorStore((s) => s.setMapView);
  const setMapStyle  = useMonitorStore((s) => s.setMapStyle);
  const setMapLabels = useMonitorStore((s) => s.setMapLabels);

  const toggleLeftPanel  = useMonitorStore((s) => s.toggleLeftPanel);
  const toggleRightPanel = useMonitorStore((s) => s.toggleRightPanel);
  const setViewState     = useMonitorStore((s) => s.setViewState);

  const flyTo = (lat: number, lng: number) => {
    setViewState({ latitude: lat, longitude: lng, zoom: 5, pitch: 30, bearing: 0, transitionDuration: 2000 } as ViewState);
  };

  const run = (fn: () => void) => { fn(); onOpenChange(false); };

  return (
    <CommandDialog open={open} onOpenChange={onOpenChange}>
      <CommandInput placeholder="Type a command or search…" />
      <CommandList>
        <CommandEmpty>No results.</CommandEmpty>

        {/* ── Navigate ─────────────────────────────────────────── */}
        <CommandGroup heading="Navigate to City">
          {CITY_PRESETS.map((city) => (
            <CommandItem
              key={city.label}
              onSelect={() => run(() => flyTo(city.lat, city.lng))}
            >
              <Navigation size={13} className="mr-2 opacity-60" />
              {city.label}
            </CommandItem>
          ))}
        </CommandGroup>

        <CommandSeparator />

        {/* ── Map controls ─────────────────────────────────────── */}
        <CommandGroup heading="Map View">
          <CommandItem onSelect={() => run(() => setMapView('3d'))} disabled={mapView === '3d'}>
            <Globe2 size={13} className="mr-2 opacity-60" />
            Switch to 3D Globe  {mapView === '3d' && '✓'}
          </CommandItem>
          <CommandItem onSelect={() => run(() => setMapView('2d'))} disabled={mapView === '2d'}>
            <Map size={13} className="mr-2 opacity-60" />
            Switch to 2D Flat  {mapView === '2d' && '✓'}
          </CommandItem>
        </CommandGroup>

        <CommandGroup heading="Map Style">
          <CommandItem onSelect={() => run(() => setMapStyle('dark'))} disabled={mapStyle === 'dark'}>
            <Globe2 size={13} className="mr-2 opacity-60" />
            Dark Matter  {mapStyle === 'dark' && '✓'}
          </CommandItem>
          <CommandItem onSelect={() => run(() => setMapStyle('street'))} disabled={mapStyle === 'street'}>
            <Map size={13} className="mr-2 opacity-60" />
            Street View  {mapStyle === 'street' && '✓'}
          </CommandItem>
          <CommandItem onSelect={() => run(() => setMapStyle('satellite'))} disabled={mapStyle === 'satellite'}>
            <Satellite size={13} className="mr-2 opacity-60" />
            Satellite  {mapStyle === 'satellite' && '✓'}
          </CommandItem>
          <CommandItem onSelect={() => run(() => setMapLabels(!mapLabels))}>
            <Tag size={13} className="mr-2 opacity-60" />
            {mapLabels ? 'Hide' : 'Show'} Country Labels
          </CommandItem>
        </CommandGroup>

        <CommandSeparator />

        {/* ── Panels ───────────────────────────────────────────── */}
        <CommandGroup heading="HUD Panels">
          <CommandItem onSelect={() => run(toggleLeftPanel)}>
            <Layers size={13} className="mr-2 opacity-60" />
            Toggle Left Panel
          </CommandItem>
          <CommandItem onSelect={() => run(toggleRightPanel)}>
            <Layers size={13} className="mr-2 opacity-60" />
            Toggle Right Panel
          </CommandItem>
        </CommandGroup>
      </CommandList>
    </CommandDialog>
  );
};

/**
 * Hook that manages CommandPalette visibility via Ctrl+K / Cmd+K.
 */
export function useCommandPalette() {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        setOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return { open, setOpen };
}
