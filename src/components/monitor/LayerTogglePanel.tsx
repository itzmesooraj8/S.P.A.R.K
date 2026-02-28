/**
 * LayerTogglePanel — 36-layer visibility grid for SPARK Globe Monitor.
 * Features: preset quick-select, group-level toggles, layer search, provider health badges.
 */
import React, { useState } from 'react';
import { useMonitorStore, type LayerId, type ProviderHealth } from '../../store/useMonitorStore';

// ── Layer metadata ────────────────────────────────────────────────────────────
interface LayerMeta {
  id: LayerId;
  label: string;
  icon: string;
  free: boolean;
  providerKey?: string;   // maps to ProviderHealth.name for status badge
}

const LAYER_GROUPS: { group: string; color: string; layers: LayerMeta[] }[] = [
  {
    group: 'Geopolitical',
    color: 'text-red-400',
    layers: [
      { id: 'conflict',     label: 'Conflict',     icon: '⚔️',  free: true,  providerKey: 'gdelt_conflict' },
      { id: 'displacement', label: 'Displacement', icon: '🏕️',  free: true  },
      { id: 'cyber',        label: 'Cyber',        icon: '🖥️',  free: true,  providerKey: 'gdelt_intel' },
      { id: 'government',   label: 'Government',   icon: '🏛️',  free: true  },
    ],
  },
  {
    group: 'Natural Hazards',
    color: 'text-orange-400',
    layers: [
      { id: 'earthquake',   label: 'Earthquake',   icon: '🌍',  free: true,  providerKey: 'usgs' },
      { id: 'wildfire',     label: 'Wildfire',     icon: '🔥',  free: true,  providerKey: 'nasa_firms' },
      { id: 'climate',      label: 'Climate',      icon: '🌡️',  free: true,  providerKey: 'eonet' },
      { id: 'volcano',      label: 'Volcano',      icon: '🌋',  free: true,  providerKey: 'eonet' },
      { id: 'flood',        label: 'Flood',        icon: '🌊',  free: true  },
      { id: 'storm',        label: 'Storm',        icon: '🌀',  free: true  },
      { id: 'disease',      label: 'Disease',      icon: '🦠',  free: true  },
    ],
  },
  {
    group: 'Infrastructure',
    color: 'text-yellow-400',
    layers: [
      { id: 'flights',      label: 'Flights',      icon: '✈️',  free: true,  providerKey: 'opensky' },
      { id: 'shipping',     label: 'Shipping',     icon: '🚢',  free: true  },
      { id: 'cables',       label: 'Cables',       icon: '🔌',  free: true  },
      { id: 'pipelines',    label: 'Pipelines',    icon: '🛢️',  free: true  },
      { id: 'datacenter',   label: 'Datacenters',  icon: '🏢',  free: true,  providerKey: 'cloudflare' },
      { id: 'infrastructure',label:'Infrastructure',icon: '🏗️', free: true  },
      { id: 'power',        label: 'Power Grid',   icon: '⚡',  free: true  },
    ],
  },
  {
    group: 'Economic',
    color: 'text-green-400',
    layers: [
      { id: 'finance',      label: 'Finance',      icon: '📈',  free: true,  providerKey: 'finnhub' },
      { id: 'crypto',       label: 'Crypto',       icon: '₿',   free: true,  providerKey: 'coingecko' },
      { id: 'energy',       label: 'Energy',       icon: '⛽',  free: false, providerKey: 'eia' },
      { id: 'economy',      label: 'Economy',      icon: '🏦',  free: true,  providerKey: 'frankfurter' },
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

// ── Layer presets ─────────────────────────────────────────────────────────────
const PRESETS: { label: string; ids: LayerId[] }[] = [
  {
    label: 'Essentials',
    ids: ['conflict', 'earthquake', 'wildfire', 'flights', 'climate', 'custom'],
  },
  {
    label: 'Hazards',
    ids: ['earthquake', 'wildfire', 'volcano', 'flood', 'storm', 'disease', 'climate'],
  },
  {
    label: 'Geopolitical',
    ids: ['conflict', 'displacement', 'cyber', 'government', 'network', 'bgp', 'leaks'],
  },
  {
    label: 'Economic',
    ids: ['finance', 'crypto', 'energy', 'economy', 'shipping', 'cables', 'pipelines'],
  },
  {
    label: 'Infra',
    ids: ['flights', 'shipping', 'cables', 'pipelines', 'datacenter', 'infrastructure', 'power'],
  },
];

// ── Provider status color helper ──────────────────────────────────────────────
function providerDotColor(status: ProviderHealth['status'] | undefined): string | null {
  if (!status) return null;
  return status === 'ok' ? '#34d399'
    : status === 'degraded' ? '#fbbf24'
    : status === 'down' ? '#f87171'
    : null; // key_required → no colored dot
}

// ── Component ─────────────────────────────────────────────────────────────────
interface Props {
  open: boolean;
  onClose: () => void;
}

export const LayerTogglePanel: React.FC<Props> = ({ open, onClose }) => {
  const visibleLayers   = useMonitorStore((s) => s.visibleLayers);
  const toggleLayer     = useMonitorStore((s) => s.toggleLayer);
  const setVisible      = useMonitorStore((s) => s.setVisibleLayers);
  const providerHealth  = useMonitorStore((s) => s.providerHealth);
  const [filter, setFilter] = useState('');

  if (!open) return null;

  const isOn = (id: LayerId) => visibleLayers.includes(id);

  const allLayerIds = LAYER_GROUPS.flatMap((g) => g.layers.map((l) => l.id));

  const q = filter.toLowerCase();
  const matchesFilter = (l: LayerMeta) =>
    !q || l.label.toLowerCase().includes(q) || l.id.toLowerCase().includes(q);

  /** Build a lookup from providerKey → health status */
  const healthByKey: Record<string, ProviderHealth['status']> = {};
  providerHealth.forEach((p) => { healthByKey[p.name] = p.status; });

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-end pt-16 pr-4"
      onClick={onClose}
    >
      <div
        className="w-80 max-h-[86vh] overflow-y-auto rounded-xl
                   border border-white/10 shadow-2xl text-sm text-gray-200"
        style={{ background: 'rgba(2,8,22,0.97)', backdropFilter: 'blur(24px)' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── Header ────────────────────────────────────────────── */}
        <div className="sticky top-0 z-10 flex items-center justify-between gap-2
                        px-4 py-2.5 border-b border-white/10"
             style={{ background: 'rgba(2,8,22,0.99)' }}>
          <span className="font-bold text-white tracking-wide text-[11px] font-mono">
            LAYER VISIBILITY
          </span>
          <div className="flex gap-1.5 text-[10px]">
            <button
              onClick={() => setVisible([...allLayerIds])}
              className="px-2 py-0.5 rounded font-mono font-bold tracking-wider transition-colors
                         bg-white/8 hover:bg-white/15 text-white/60 hover:text-white"
            >
              ALL
            </button>
            <button
              onClick={() => setVisible([])}
              className="px-2 py-0.5 rounded font-mono font-bold tracking-wider transition-colors
                         bg-white/8 hover:bg-white/15 text-white/60 hover:text-white"
            >
              NONE
            </button>
          </div>
          <button onClick={onClose} className="ml-1 text-gray-400 hover:text-white text-lg leading-none">
            ✕
          </button>
        </div>

        {/* ── Preset quick-select ────────────────────────────────── */}
        <div className="px-3 py-2 border-b border-white/8 flex flex-wrap gap-1.5">
          {PRESETS.map((preset) => {
            const isActive =
              preset.ids.length === visibleLayers.length &&
              preset.ids.every(isOn);
            return (
              <button
                key={preset.label}
                onClick={() => setVisible([...preset.ids])}
                className="px-2 py-0.5 rounded-full text-[9px] font-mono font-bold tracking-widest
                           transition-all duration-150"
                style={{
                  background: isActive ? 'rgba(0,245,255,0.15)' : 'rgba(255,255,255,0.07)',
                  border: `1px solid ${isActive ? 'rgba(0,245,255,0.45)' : 'rgba(255,255,255,0.12)'}`,
                  color: isActive ? '#00f5ff' : 'rgba(255,255,255,0.5)',
                }}
              >
                {preset.label}
              </button>
            );
          })}
        </div>

        {/* ── Search ────────────────────────────────────────────── */}
        <div className="px-3 py-2 border-b border-white/8">
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter layers…"
            className="w-full rounded-lg px-3 py-1.5 text-[11px] text-white
                       placeholder-gray-500 outline-none transition-colors font-mono"
            style={{
              background: 'rgba(255,255,255,0.06)',
              border: '1px solid rgba(255,255,255,0.12)',
            }}
          />
        </div>

        {/* ── Groups ────────────────────────────────────────────── */}
        <div className="px-3 py-2 space-y-4">
          {LAYER_GROUPS.map((group) => {
            const visible = group.layers.filter(matchesFilter);
            if (visible.length === 0) return null;

            const groupIds = group.layers.map((l) => l.id);
            const allGroupOn  = groupIds.every(isOn);
            const anyGroupOn  = groupIds.some(isOn);

            return (
              <div key={group.group}>
                {/* Group header with toggle */}
                <div className="flex items-center justify-between mb-2">
                  <h3 className={`text-[9px] font-bold uppercase tracking-[0.18em] font-mono ${group.color}`}>
                    {group.group}
                  </h3>
                  <div className="flex items-center gap-1">
                    <span className="text-[8px] font-mono text-white/25">
                      {groupIds.filter(isOn).length}/{groupIds.length}
                    </span>
                    <button
                      onClick={() => {
                        if (allGroupOn) {
                          setVisible(visibleLayers.filter((id) => !groupIds.includes(id)));
                        } else {
                          const newSet = new Set([...visibleLayers, ...groupIds]);
                          setVisible([...newSet]);
                        }
                      }}
                      className="text-[8px] font-mono px-1.5 py-0.5 rounded transition-colors"
                      style={{
                        background: anyGroupOn ? 'rgba(255,255,255,0.1)' : 'rgba(255,255,255,0.05)',
                        color: allGroupOn ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.35)',
                      }}
                    >
                      {allGroupOn ? 'OFF' : 'ON'}
                    </button>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-1.5">
                  {visible.map((layer) => {
                    const on = isOn(layer.id);
                    const pStatus = layer.providerKey ? healthByKey[layer.providerKey] : undefined;
                    const dotColor = providerDotColor(pStatus);

                    return (
                      <button
                        key={layer.id}
                        onClick={() => toggleLayer(layer.id)}
                        className={`
                          flex items-center gap-2 px-2.5 py-1.5 rounded-lg text-left
                          transition-all duration-150
                          ${on
                            ? 'bg-white/12 text-white'
                            : 'bg-white/4 text-gray-500 hover:bg-white/9 hover:text-gray-300'}
                        `}
                      >
                        <span className="text-base leading-none">{layer.icon}</span>
                        <span className="truncate text-[10px] font-medium">{layer.label}</span>
                        {!layer.free && (
                          <span className="ml-auto text-[8px] text-yellow-500 shrink-0 font-mono">KEY</span>
                        )}
                        {/* Provider health dot */}
                        {dotColor && (
                          <span
                            className="ml-auto shrink-0 w-1.5 h-1.5 rounded-full"
                            style={{ background: dotColor, boxShadow: `0 0 4px ${dotColor}` }}
                          />
                        )}
                        {/* Active indicator when no health dot */}
                        {!dotColor && (
                          <span className={`ml-auto shrink-0 w-1.5 h-1.5 rounded-full ${on ? 'bg-white/40' : 'bg-white/10'}`} />
                        )}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </div>

        {/* ── Footer ─────────────────────────────────────────────── */}
        <div className="sticky bottom-0 px-4 py-2 border-t border-white/10
                        text-[9px] font-mono text-white/30 text-right"
             style={{ background: 'rgba(2,8,22,0.99)' }}>
          {visibleLayers.length} / {allLayerIds.length} layers active
        </div>
      </div>
    </div>
  );
};


