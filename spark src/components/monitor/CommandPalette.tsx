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

/* ── World cities organized by region ────────────────────────────────────── */
const CITIES_BY_REGION = [
  {
    region: '🌎 North America',
    cities: [
      { label: 'New York',        lat: 40.71,  lng: -74.01  },
      { label: 'Los Angeles',     lat: 34.05,  lng: -118.24 },
      { label: 'Chicago',         lat: 41.88,  lng: -87.63  },
      { label: 'Houston',         lat: 29.76,  lng: -95.37  },
      { label: 'Miami',           lat: 25.77,  lng: -80.19  },
      { label: 'Washington DC',   lat: 38.91,  lng: -77.04  },
      { label: 'San Francisco',   lat: 37.77,  lng: -122.42 },
      { label: 'Seattle',         lat: 47.61,  lng: -122.33 },
      { label: 'Las Vegas',       lat: 36.17,  lng: -115.14 },
      { label: 'Boston',          lat: 42.36,  lng: -71.06  },
      { label: 'Atlanta',         lat: 33.75,  lng: -84.39  },
      { label: 'Dallas',          lat: 32.78,  lng: -96.80  },
      { label: 'Phoenix',         lat: 33.45,  lng: -112.07 },
      { label: 'Toronto',         lat: 43.65,  lng: -79.38  },
      { label: 'Montreal',        lat: 45.50,  lng: -73.57  },
      { label: 'Vancouver',       lat: 49.28,  lng: -123.12 },
      { label: 'Mexico City',     lat: 19.43,  lng: -99.13  },
      { label: 'Guadalajara',     lat: 20.66,  lng: -103.35 },
      { label: 'Havana',          lat: 23.14,  lng: -82.36  },
      { label: 'Panama City',     lat: 8.99,   lng: -79.52  },
      { label: 'San José',        lat: 9.93,   lng: -84.08  },
      { label: 'Guatemala City',  lat: 14.64,  lng: -90.51  },
    ],
  },
  {
    region: '🌎 South America',
    cities: [
      { label: 'São Paulo',       lat: -23.55, lng: -46.63  },
      { label: 'Rio de Janeiro',  lat: -22.91, lng: -43.17  },
      { label: 'Buenos Aires',    lat: -34.60, lng: -58.38  },
      { label: 'Lima',            lat: -12.05, lng: -77.04  },
      { label: 'Bogotá',          lat: 4.71,   lng: -74.07  },
      { label: 'Santiago',        lat: -33.45, lng: -70.67  },
      { label: 'Caracas',         lat: 10.48,  lng: -66.88  },
      { label: 'Quito',           lat: -0.22,  lng: -78.51  },
      { label: 'La Paz',          lat: -16.50, lng: -68.15  },
      { label: 'Montevideo',      lat: -34.90, lng: -56.19  },
      { label: 'Asunción',        lat: -25.28, lng: -57.64  },
      { label: 'Medellín',        lat: 6.25,   lng: -75.56  },
      { label: 'Brasília',        lat: -15.78, lng: -47.93  },
      { label: 'Manaus',          lat: -3.10,  lng: -60.02  },
    ],
  },
  {
    region: '🌍 Europe',
    cities: [
      { label: 'London',          lat: 51.51,  lng: -0.13   },
      { label: 'Paris',           lat: 48.86,  lng: 2.35    },
      { label: 'Berlin',          lat: 52.52,  lng: 13.40   },
      { label: 'Madrid',          lat: 40.42,  lng: -3.70   },
      { label: 'Barcelona',       lat: 41.39,  lng: 2.15    },
      { label: 'Rome',            lat: 41.90,  lng: 12.50   },
      { label: 'Milan',           lat: 45.46,  lng: 9.19    },
      { label: 'Amsterdam',       lat: 52.37,  lng: 4.90    },
      { label: 'Brussels',        lat: 50.85,  lng: 4.35    },
      { label: 'Vienna',          lat: 48.21,  lng: 16.37   },
      { label: 'Warsaw',          lat: 52.23,  lng: 21.01   },
      { label: 'Prague',          lat: 50.08,  lng: 14.44   },
      { label: 'Stockholm',       lat: 59.33,  lng: 18.07   },
      { label: 'Oslo',            lat: 59.91,  lng: 10.75   },
      { label: 'Helsinki',        lat: 60.17,  lng: 24.94   },
      { label: 'Copenhagen',      lat: 55.68,  lng: 12.57   },
      { label: 'Lisbon',          lat: 38.72,  lng: -9.14   },
      { label: 'Athens',          lat: 37.98,  lng: 23.73   },
      { label: 'Budapest',        lat: 47.50,  lng: 19.04   },
      { label: 'Bucharest',       lat: 44.43,  lng: 26.10   },
      { label: 'Kyiv',            lat: 50.45,  lng: 30.52   },
      { label: 'Moscow',          lat: 55.75,  lng: 37.62   },
      { label: 'Saint Petersburg', lat: 59.95, lng: 30.32   },
      { label: 'Zurich',          lat: 47.38,  lng: 8.54    },
      { label: 'Geneva',          lat: 46.20,  lng: 6.15    },
      { label: 'Dublin',          lat: 53.33,  lng: -6.25   },
      { label: 'Edinburgh',       lat: 55.95,  lng: -3.19   },
      { label: 'Manchester',      lat: 53.48,  lng: -2.24   },
      { label: 'Hamburg',         lat: 53.55,  lng: 9.99    },
      { label: 'Munich',          lat: 48.14,  lng: 11.58   },
      { label: 'Lyon',            lat: 45.75,  lng: 4.85    },
      { label: 'Porto',           lat: 41.16,  lng: -8.62   },
      { label: 'Belgrade',        lat: 44.82,  lng: 20.46   },
      { label: 'Sofia',           lat: 42.70,  lng: 23.32   },
      { label: 'Minsk',           lat: 53.90,  lng: 27.57   },
      { label: 'Riga',            lat: 56.95,  lng: 24.11   },
      { label: 'Tallinn',         lat: 59.44,  lng: 24.75   },
      { label: 'Vilnius',         lat: 54.69,  lng: 25.28   },
      { label: 'Reykjavik',       lat: 64.13,  lng: -21.82  },
    ],
  },
  {
    region: '🌏 Asia',
    cities: [
      { label: 'Tokyo',           lat: 35.68,  lng: 139.69  },
      { label: 'Beijing',         lat: 39.91,  lng: 116.39  },
      { label: 'Shanghai',        lat: 31.23,  lng: 121.47  },
      { label: 'Hong Kong',       lat: 22.32,  lng: 114.17  },
      { label: 'Shenzhen',        lat: 22.54,  lng: 114.06  },
      { label: 'Guangzhou',       lat: 23.13,  lng: 113.26  },
      { label: 'Chengdu',         lat: 30.57,  lng: 104.07  },
      { label: 'Chongqing',       lat: 29.56,  lng: 106.55  },
      { label: 'Wuhan',           lat: 30.59,  lng: 114.31  },
      { label: 'Seoul',           lat: 37.57,  lng: 126.98  },
      { label: 'Busan',           lat: 35.18,  lng: 129.08  },
      { label: 'Osaka',           lat: 34.69,  lng: 135.50  },
      { label: 'Taipei',          lat: 25.03,  lng: 121.57  },
      { label: 'Singapore',       lat: 1.35,   lng: 103.82  },
      { label: 'Kuala Lumpur',    lat: 3.14,   lng: 101.69  },
      { label: 'Bangkok',         lat: 13.75,  lng: 100.52  },
      { label: 'Jakarta',         lat: -6.21,  lng: 106.85  },
      { label: 'Manila',          lat: 14.60,  lng: 120.98  },
      { label: 'Ho Chi Minh City', lat: 10.82, lng: 106.63  },
      { label: 'Hanoi',           lat: 21.03,  lng: 105.85  },
      { label: 'Yangon',          lat: 16.87,  lng: 96.19   },
      { label: 'Phnom Penh',      lat: 11.56,  lng: 104.92  },
      { label: 'Mumbai',          lat: 19.08,  lng: 72.88   },
      { label: 'Delhi',           lat: 28.66,  lng: 77.22   },
      { label: 'Bangalore',       lat: 12.97,  lng: 77.59   },
      { label: 'Chennai',         lat: 13.09,  lng: 80.27   },
      { label: 'Kolkata',         lat: 22.57,  lng: 88.36   },
      { label: 'Hyderabad',       lat: 17.39,  lng: 78.49   },
      { label: 'Karachi',         lat: 24.86,  lng: 67.01   },
      { label: 'Lahore',          lat: 31.56,  lng: 74.34   },
      { label: 'Dhaka',           lat: 23.72,  lng: 90.41   },
      { label: 'Colombo',         lat: 6.93,   lng: 79.85   },
      { label: 'Kathmandu',       lat: 27.72,  lng: 85.32   },
      { label: 'Kabul',           lat: 34.53,  lng: 69.17   },
      { label: 'Tashkent',        lat: 41.30,  lng: 69.24   },
      { label: 'Almaty',          lat: 43.24,  lng: 76.92   },
    ],
  },
  {
    region: '🌏 Middle East',
    cities: [
      { label: 'Dubai',           lat: 25.20,  lng: 55.27   },
      { label: 'Abu Dhabi',       lat: 24.45,  lng: 54.38   },
      { label: 'Riyadh',          lat: 24.69,  lng: 46.72   },
      { label: 'Jeddah',          lat: 21.49,  lng: 39.19   },
      { label: 'Doha',            lat: 25.29,  lng: 51.53   },
      { label: 'Kuwait City',     lat: 29.37,  lng: 47.98   },
      { label: 'Muscat',          lat: 23.61,  lng: 58.59   },
      { label: 'Manama',          lat: 26.22,  lng: 50.59   },
      { label: 'Amman',           lat: 31.96,  lng: 35.95   },
      { label: 'Beirut',          lat: 33.89,  lng: 35.50   },
      { label: 'Damascus',        lat: 33.51,  lng: 36.29   },
      { label: 'Baghdad',         lat: 33.34,  lng: 44.40   },
      { label: 'Tehran',          lat: 35.69,  lng: 51.42   },
      { label: 'Istanbul',        lat: 41.01,  lng: 28.96   },
      { label: 'Ankara',          lat: 39.93,  lng: 32.86   },
      { label: 'Tel Aviv',        lat: 32.08,  lng: 34.78   },
      { label: 'Jerusalem',       lat: 31.77,  lng: 35.22   },
      { label: 'Sanaa',           lat: 15.35,  lng: 44.21   },
    ],
  },
  {
    region: '🌍 Africa',
    cities: [
      { label: 'Lagos',           lat: 6.52,   lng: 3.38    },
      { label: 'Abuja',           lat: 9.06,   lng: 7.50    },
      { label: 'Cairo',           lat: 30.04,  lng: 31.24   },
      { label: 'Alexandria',      lat: 31.20,  lng: 29.92   },
      { label: 'Johannesburg',    lat: -26.20, lng: 28.04   },
      { label: 'Cape Town',       lat: -33.92, lng: 18.42   },
      { label: 'Durban',          lat: -29.86, lng: 31.02   },
      { label: 'Nairobi',         lat: -1.29,  lng: 36.82   },
      { label: 'Accra',           lat: 5.56,   lng: -0.20   },
      { label: 'Addis Ababa',     lat: 9.02,   lng: 38.75   },
      { label: 'Dar es Salaam',   lat: -6.79,  lng: 39.21   },
      { label: 'Kigali',          lat: -1.95,  lng: 30.06   },
      { label: 'Kampala',         lat: 0.32,   lng: 32.58   },
      { label: 'Dakar',           lat: 14.69,  lng: -17.44  },
      { label: 'Abidjan',         lat: 5.35,   lng: -4.01   },
      { label: 'Casablanca',      lat: 33.59,  lng: -7.62   },
      { label: 'Tunis',           lat: 36.82,  lng: 10.17   },
      { label: 'Algiers',         lat: 36.74,  lng: 3.07    },
      { label: 'Tripoli',         lat: 32.90,  lng: 13.18   },
      { label: 'Khartoum',        lat: 15.55,  lng: 32.53   },
      { label: 'Kinshasa',        lat: -4.32,  lng: 15.32   },
      { label: 'Luanda',          lat: -8.84,  lng: 13.23   },
      { label: 'Harare',          lat: -17.83, lng: 31.05   },
      { label: 'Lusaka',          lat: -15.42, lng: 28.28   },
      { label: 'Maputo',          lat: -25.97, lng: 32.57   },
      { label: 'Antananarivo',    lat: -18.91, lng: 47.54   },
      { label: 'Bamako',          lat: 12.65,  lng: -8.00   },
      { label: 'Conakry',         lat: 9.54,   lng: -13.68  },
      { label: 'Mogadishu',       lat: 2.05,   lng: 45.34   },
    ],
  },
  {
    region: '🌏 Oceania',
    cities: [
      { label: 'Sydney',          lat: -33.87, lng: 151.21  },
      { label: 'Melbourne',       lat: -37.81, lng: 144.96  },
      { label: 'Brisbane',        lat: -27.47, lng: 153.03  },
      { label: 'Perth',           lat: -31.95, lng: 115.86  },
      { label: 'Adelaide',        lat: -34.93, lng: 138.60  },
      { label: 'Canberra',        lat: -35.28, lng: 149.13  },
      { label: 'Auckland',        lat: -36.87, lng: 174.77  },
      { label: 'Wellington',      lat: -41.29, lng: 174.78  },
      { label: 'Christchurch',    lat: -43.53, lng: 172.64  },
      { label: 'Port Moresby',    lat: -9.44,  lng: 147.18  },
      { label: 'Suva',            lat: -18.14, lng: 178.44  },
    ],
  },
] as const;

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

        {/* ── Navigate by region ──────────────────────────────── */}
        {CITIES_BY_REGION.map(({ region, cities }) => (
          <CommandGroup key={region} heading={region}>
            {cities.map((city) => (
              <CommandItem
                key={city.label}
                onSelect={() => run(() => flyTo(city.lat, city.lng))}
              >
                <Navigation size={13} className="mr-2 opacity-60" />
                {city.label}
              </CommandItem>
            ))}
          </CommandGroup>
        ))}

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
