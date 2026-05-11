import { useState } from 'react';
import { Puzzle, RefreshCw, Power, AlertTriangle, CheckCircle, Loader2, XCircle } from 'lucide-react';
import { usePlugins } from '@/hooks/usePlugins';
import type { Plugin } from '@/hooks/usePlugins';

const STATUS_CONFIG = {
  active:   { color: '#30d158', icon: CheckCircle,  label: 'ACTIVE'   },
  inactive: { color: '#636366', icon: Power,         label: 'INACTIVE' },
  error:    { color: '#ff453a', icon: XCircle,       label: 'ERROR'    },
  loading:  { color: '#ff9f0a', icon: Loader2,       label: 'LOADING'  },
};

const CATEGORY_COLORS: Record<string, string> = {
  'AI Core':        '#00f5ff',
  'Memory':         '#0066ff',
  'Voice':          '#00ff88',
  'Vision':         '#8b00ff',
  'Tools':          '#ff9f0a',
  'Intelligence':   '#ff453a',
  'Integrations':   '#ff6bff',
  'Security':       '#30d158',
};

function PluginCard({ plugin, onToggle }: { plugin: Plugin; onToggle: (id: string, enable: boolean) => void }) {
  const cfg = STATUS_CONFIG[plugin.status] ?? STATUS_CONFIG.inactive;
  const Icon = cfg.icon;
  const catColor = CATEGORY_COLORS[plugin.category] ?? '#00f5ff';

  return (
    <div
      className="hud-panel rounded p-3 flex flex-col gap-2 transition-all duration-200 hover:border-hud-cyan/40"
      style={{ borderLeft: `3px solid ${cfg.color}` }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="font-orbitron text-[10px] text-hud-cyan truncate">{plugin.name}</div>
          <div className="font-mono-tech text-[8px] text-hud-cyan/40 mt-0.5">{plugin.id}</div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <span
            className="font-orbitron text-[7px] px-1.5 py-0.5 rounded"
            style={{ color: catColor, background: `${catColor}18`, border: `1px solid ${catColor}40` }}
          >
            {plugin.category}
          </span>
          <div className="flex items-center gap-1" style={{ color: cfg.color }}>
            <Icon size={10} className={plugin.status === 'loading' ? 'animate-spin' : ''} />
            <span className="font-orbitron text-[7px]">{cfg.label}</span>
          </div>
        </div>
      </div>

      <div className="font-mono-tech text-[8px] text-hud-cyan/50 leading-relaxed line-clamp-2">
        {plugin.description}
      </div>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-mono-tech text-[7px] text-hud-cyan/30">v{plugin.version}</span>
          {plugin.error_count > 0 && (
            <div className="flex items-center gap-0.5 text-hud-red/70">
              <AlertTriangle size={8} />
              <span className="font-mono-tech text-[7px]">{plugin.error_count} err</span>
            </div>
          )}
          {plugin.uptime > 0 && (
            <span className="font-mono-tech text-[7px] text-hud-green/60">
              {Math.floor(plugin.uptime / 60)}m uptime
            </span>
          )}
        </div>
        <button
          onClick={() => onToggle(plugin.id, !plugin.enabled)}
          className={`font-orbitron text-[8px] px-2 py-0.5 rounded border transition-all duration-150 ${
            plugin.enabled
              ? 'border-hud-red/40 text-hud-red/70 hover:border-hud-red hover:text-hud-red'
              : 'border-hud-green/40 text-hud-green/70 hover:border-hud-green hover:text-hud-green'
          }`}
        >
          {plugin.enabled ? 'DISABLE' : 'ENABLE'}
        </button>
      </div>
    </div>
  );
}

export default function PluginsModule() {
  const { plugins, stats, isLoading, enablePlugin, disablePlugin, reloadAll, isToggling } = usePlugins();
  const [filter, setFilter] = useState<string>('ALL');
  const [search, setSearch] = useState('');

  const categories = ['ALL', ...Array.from(new Set(plugins.map(p => p.category)))];

  const filtered = plugins.filter(p => {
    const matchesCat  = filter === 'ALL' || p.category === filter;
    const matchSearch = search === '' || p.name.toLowerCase().includes(search.toLowerCase()) || p.id.includes(search.toLowerCase());
    return matchesCat && matchSearch;
  });

  const handleToggle = (id: string, enable: boolean) => {
    if (enable) enablePlugin(id);
    else disablePlugin(id);
  };

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="px-4 pt-3 pb-2 border-b border-hud-cyan/20 shrink-0">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Puzzle size={14} className="text-hud-cyan" />
            <span className="font-orbitron text-xs tracking-widest neon-text">PLUGIN MANAGER</span>
            {isLoading && <Loader2 size={12} className="text-hud-cyan/50 animate-spin" />}
          </div>
          <button
            onClick={() => reloadAll()}
            disabled={isToggling}
            className="flex items-center gap-1 font-orbitron text-[8px] px-2 py-1 rounded border border-hud-cyan/30 text-hud-cyan/60 hover:border-hud-cyan/60 hover:text-hud-cyan transition-all"
          >
            <RefreshCw size={10} className={isToggling ? 'animate-spin' : ''} />
            RELOAD ALL
          </button>
        </div>

        {/* Stats row */}
        {stats && (
          <div className="grid grid-cols-4 gap-2 mb-3">
            {[
              { label: 'TOTAL',    value: stats.total,    color: '#00f5ff' },
              { label: 'ACTIVE',   value: stats.active,   color: '#30d158' },
              { label: 'INACTIVE', value: stats.inactive, color: '#636366' },
              { label: 'ERROR',    value: stats.error,    color: '#ff453a' },
            ].map(s => (
              <div key={s.label} className="hud-panel rounded p-2 text-center">
                <div className="font-orbitron text-sm font-bold" style={{ color: s.color }}>{s.value}</div>
                <div className="font-orbitron text-[7px] text-hud-cyan/40">{s.label}</div>
              </div>
            ))}
          </div>
        )}

        {/* Search */}
        <input
          value={search}
          onChange={e => setSearch(e.target.value)}
          placeholder="SEARCH PLUGINS..."
          className="w-full bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[9px] text-hud-cyan placeholder:text-hud-cyan/30 outline-none focus:border-hud-cyan/50 mb-2"
        />

        {/* Category filter */}
        <div className="flex flex-wrap gap-1">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`font-orbitron text-[7px] px-2 py-0.5 rounded border transition-all ${
                filter === cat
                  ? 'border-hud-cyan text-hud-cyan bg-hud-cyan/10'
                  : 'border-hud-cyan/20 text-hud-cyan/40 hover:border-hud-cyan/50'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Plugin list */}
      <div className="flex-1 overflow-y-auto scrollbar-hud p-3 flex flex-col gap-2">
        {isLoading && !plugins.length ? (
          <div className="flex items-center justify-center h-32 text-hud-cyan/40">
            <div className="text-center">
              <Loader2 size={24} className="mx-auto mb-2 animate-spin" />
              <span className="font-orbitron text-[9px] tracking-widest">LOADING PLUGINS...</span>
            </div>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex items-center justify-center h-32 text-hud-cyan/30">
            <span className="font-orbitron text-[9px]">NO PLUGINS FOUND</span>
          </div>
        ) : (
          filtered.map(plugin => (
            <PluginCard key={plugin.id} plugin={plugin} onToggle={handleToggle} />
          ))
        )}
      </div>
    </div>
  );
}
