/**
 * LayerTogglePanel — 36-layer visibility grid for Globe Monitor.
 * Grouped by category. Persisted in Zustand store (visibleLayers).
 */
import React, { useState } from 'react';
import { useMonitorStore, type LayerId } from '../../store/useMonitorStore';

// ── Layer metadata ────────────────────────────────────────────────────────────
interface LayerMeta {
  id: LayerId;
  label: string;
  icon: string;  // emoji / unicode icon
  free: boolean; // false = key required
}

const LAYER_GROUPS: { group: string; color: string; layers: LayerMeta[] }[] = [
  {
    group: 'Geopolitical',
    color: 'text-red-400',
    layers: [
      { id: 'conflict',     label: 'Conflict',     icon: '⚔️',  free: true  },
      { id: 'displacement', label: 'Displacement', icon: '🏕️',  free: true  },
      { id: 'cyber',        label: 'Cyber',        icon: '🖥️',  free: true  },
      { id: 'government',   label: 'Government',   icon: '🏛️',  free: true  },
    ],
  },
  {
    group: 'Natural Hazards',
    color: 'text-orange-400',
    layers: [
      { id: 'earthquake',   label: 'Earthquake',   icon: '🌍',  free: true  },
      { id: 'wildfire',     label: 'Wildfire',     icon: '🔥',  free: true  },
      { id: 'climate',      label: 'Climate',      icon: '🌡️',  free: true  },
      { id: 'volcano',      label: 'Volcano',      icon: '🌋',  free: true  },
      { id: 'flood',        label: 'Flood',        icon: '🌊',  free: true  },
      { id: 'storm',        label: 'Storm',        icon: '🌀',  free: true  },
      { id: 'disease',      label: 'Disease',      icon: '🦠',  free: true  },
    ],
  },
  {
    group: 'Infrastructure',
    color: 'text-yellow-400',
    layers: [
      { id: 'flights',      label: 'Flights',      icon: '✈️',  free: true  },
      { id: 'shipping',     label: 'Shipping',     icon: '🚢',  free: true  },
      { id: 'cables',       label: 'Cables',       icon: '🔌',  free: true  },
      { id: 'pipelines',    label: 'Pipelines',    icon: '🛢️',  free: true  },
      { id: 'datacenter',   label: 'Datacenters',  icon: '🏢',  free: true  },
      { id: 'infrastructure',label:'Infrastructure',icon: '🏗️',  free: true  },
      { id: 'power',        label: 'Power Grid',   icon: '⚡',  free: true  },
    ],
  },
  {
    group: 'Economic',
    color: 'text-green-400',
    layers: [
      { id: 'finance',      label: 'Finance',      icon: '📈',  free: true  },
      { id: 'crypto',       label: 'Crypto',       icon: '₿',   free: true  },
      { id: 'energy',       label: 'Energy',       icon: '⛽',  free: false },
      { id: 'economy',      label: 'Economy',      icon: '🏦',  free: true  },
    ],
  },
  {
    group: 'Environmental',
    color: 'text-teal-400',
    layers: [
      { id: 'airquality',   label: 'Air Quality',  icon: '💨',  free: true  },
      { id: 'radiation',    label: 'Radiation',    icon: '☢️',  free: true  },
      { id: 'deforestation',label: 'Deforestation',icon: '🌲',  free: true  },
    ],
  },
  {
    group: 'Intelligence',
    color: 'text-purple-400',
    layers: [
      { id: 'network',      label: 'Network',      icon: '🌐',  free: true  },
      { id: 'bgp',          label: 'BGP Routing',  icon: '📡',  free: true  },
      { id: 'leaks',        label: 'Data Leaks',   icon: '🔓',  free: true  },
      { id: 'custom',       label: 'Custom',       icon: '🔍',  free: true  },
    ],
  },
  {
    group: 'Space',
    color: 'text-blue-400',
    layers: [
      { id: 'satellites',   label: 'Satellites',   icon: '🛰️',  free: true  },
      { id: 'solar',        label: 'Solar Activity',icon: '☀️',  free: true  },
    ],
  },
];

// ── Component ─────────────────────────────────────────────────────────────────
interface Props {
  open: boolean;
  onClose: () => void;
}

export const LayerTogglePanel: React.FC<Props> = ({ open, onClose }) => {
  const visibleLayers = useMonitorStore((s) => s.visibleLayers);
  const toggleLayer   = useMonitorStore((s) => s.toggleLayer);
  const setVisible    = useMonitorStore((s) => s.setVisibleLayers);
  const [filter,  setFilter]  = useState('');

  if (!open) return null;

  const isOn = (id: LayerId) => visibleLayers.includes(id);

  const allLayerIds = LAYER_GROUPS.flatMap((g) => g.layers.map((l) => l.id));
  const allOn  = allLayerIds.every(isOn);
  const allOff = allLayerIds.every((id) => !isOn(id));

  const q = filter.toLowerCase();
  const matchesFilter = (l: LayerMeta) =>
    !q || l.label.toLowerCase().includes(q) || l.id.toLowerCase().includes(q);

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end pt-16 pr-4"
      onClick={onClose}
    >
      <div
        className="w-80 max-h-[80vh] overflow-y-auto rounded-xl
                   border border-white/10 bg-gray-900/95 backdrop-blur-md
                   shadow-2xl text-sm text-gray-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between gap-2
                        px-4 py-3 border-b border-white/10 bg-gray-900/95">
          <span className="font-bold text-white tracking-wide">Layer Visibility</span>
          <div className="flex gap-2 text-xs">
            <button
              onClick={() => setVisible([...allLayerIds])}
              className="px-2 py-0.5 rounded bg-white/10 hover:bg-white/20"
            >
              All on
            </button>
            <button
              onClick={() => setVisible([])}
              className="px-2 py-0.5 rounded bg-white/10 hover:bg-white/20"
            >
              All off
            </button>
          </div>
          <button onClick={onClose} className="ml-1 text-gray-400 hover:text-white text-lg leading-none">
            ✕
          </button>
        </div>

        {/* Search */}
        <div className="px-4 py-2 border-b border-white/10">
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter layers…"
            className="w-full rounded bg-white/10 px-3 py-1.5 text-sm text-white
                       placeholder-gray-500 outline-none border border-transparent
                       focus:border-blue-500/60"
          />
        </div>

        {/* Groups */}
        <div className="px-3 py-2 space-y-4">
          {LAYER_GROUPS.map((group) => {
            const visible = group.layers.filter(matchesFilter);
            if (visible.length === 0) return null;
            return (
              <div key={group.group}>
                <h3 className={`text-xs font-semibold uppercase tracking-widest mb-2 ${group.color}`}>
                  {group.group}
                </h3>
                <div className="grid grid-cols-2 gap-1.5">
                  {visible.map((layer) => {
                    const on = isOn(layer.id);
                    return (
                      <button
                        key={layer.id}
                        onClick={() => toggleLayer(layer.id)}
                        className={`
                          flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left
                          transition-colors duration-150
                          ${on
                            ? 'bg-white/15 text-white'
                            : 'bg-white/5 text-gray-500 hover:bg-white/10 hover:text-gray-300'}
                        `}
                      >
                        <span className="text-base leading-none">{layer.icon}</span>
                        <span className="truncate text-xs font-medium">{layer.label}</span>
                        {!layer.free && (
                          <span className="ml-auto text-[10px] text-yellow-500 shrink-0">KEY</span>
                        )}
                        <span className={`ml-auto shrink-0 w-2 h-2 rounded-full ${on ? 'bg-green-400' : 'bg-gray-600'}`} />
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* Footer count */}
        <div className="sticky bottom-0 px-4 py-2 border-t border-white/10 bg-gray-900/95
                        text-xs text-gray-500 text-right">
          {visibleLayers.length} / {allLayerIds.length} layers active
        </div>
      </div>
    </div>
  );
};
