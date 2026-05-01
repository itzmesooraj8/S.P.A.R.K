import { useState, useEffect } from 'react';
import { Brain, Cpu, Database, Zap, X, GitCommit } from 'lucide-react';
import { useDevState } from '@/hooks/useDevState';

const API = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

const EMOTIONS = [
  { emoji: '🤖', label: 'NEUTRAL', color: '#00f5ff' },
  { emoji: '🧐', label: 'ANALYZING', color: '#ffb800' },
  { emoji: '⚡', label: 'ENERGIZED', color: '#00ff88' },
  { emoji: '🛡️', label: 'GUARDED', color: '#ff3b3b' },
];

const PLUGINS = [
  { id: 'neural_search', name: 'NEURAL SEARCH' },
  { id: 'code_sandbox', name: 'CODE EXECUTOR' },
  { id: 'web_browser', name: 'WEB BROWSER' },
  { id: 'vision', name: 'IMAGE VISION' },
  { id: 'tts', name: 'VOICE SYNTH' },
];

interface PluginApiItem {
  id: string;
  enabled: boolean;
}

interface PluginListResponse {
  plugins?: PluginApiItem[];
}

interface ModelStatusItem {
  name: string;
  available: boolean;
  avg_latency_ms?: number;
  attempts?: number;
}

interface ModelsStatusResponse {
  models?: ModelStatusItem[];
  local_running?: string[];
}

interface ActiveModelResponse {
  model?: string;
}

interface Props { onClose: () => void; }

export default function AIPanelSlider({ onClose }: Props) {
  const devState = useDevState();
  const [memUsage] = useState(67);
  const [contextScore] = useState(84);
  const [emotionIdx, setEmotionIdx] = useState(0);
  const [plugins, setPlugins] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(PLUGINS.map((plugin) => [plugin.id, false])) as Record<string, boolean>,
  );
  const [learningMode, setLearningMode] = useState(true);
  const [activeModel, setActiveModel] = useState('');
  const [modelOnline, setModelOnline] = useState(false);
  const [avgLatencyMs, setAvgLatencyMs] = useState<number | null>(null);

  useEffect(() => {
    const t = setInterval(() => {
      if (Math.random() > 0.95) setEmotionIdx(i => (i + 1) % EMOTIONS.length);
    }, 800);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    let cancelled = false;

    const refreshPlugins = async () => {
      try {
        const res = await fetch(`${API}/api/plugins`);
        if (!res.ok) return;

        const data = (await res.json()) as PluginListResponse;
        if (cancelled) return;

        const fromApi = new Map((data.plugins ?? []).map((plugin) => [plugin.id, !!plugin.enabled]));
        setPlugins((prev) => {
          const next = { ...prev };
          PLUGINS.forEach((plugin) => {
            if (fromApi.has(plugin.id)) {
              next[plugin.id] = !!fromApi.get(plugin.id);
            }
          });
          return next;
        });
      } catch {
        // keep panel resilient during backend reconnects
      }
    };

    refreshPlugins();
    const timer = window.setInterval(refreshPlugins, 5000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const refreshModelHealth = async () => {
      try {
        const [statusRes, activeRes] = await Promise.all([
          fetch(`${API}/api/models/status`),
          fetch(`${API}/api/models/active`),
        ]);
        if (!statusRes.ok || !activeRes.ok) return;

        const statusData = (await statusRes.json()) as ModelsStatusResponse;
        const activeData = (await activeRes.json()) as ActiveModelResponse;
        if (cancelled) return;

        const selected = (activeData.model || '').trim();
        const modelInfo = (statusData.models || []).find((m) => m.name === selected);
        const localRunning = Array.isArray(statusData.local_running)
          ? statusData.local_running
          : [];
        const activeLocal = selected ? localRunning.includes(selected) : false;

        setActiveModel(selected);
        setModelOnline(modelInfo ? Boolean(modelInfo.available) : activeLocal);
        if (
          typeof modelInfo?.avg_latency_ms === 'number'
          && Number.isFinite(modelInfo.avg_latency_ms)
          && modelInfo.avg_latency_ms > 0
          && (modelInfo.attempts || 0) > 0
        ) {
          setAvgLatencyMs(modelInfo.avg_latency_ms);
        } else {
          setAvgLatencyMs(null);
        }
      } catch {
        // ignore transient backend errors
      }
    };

    refreshModelHealth();
    const timer = window.setInterval(refreshModelHealth, 3000);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const togglePlugin = async (pluginId: string) => {
    const current = !!plugins[pluginId];
    const action = current ? 'disable' : 'enable';

    setPlugins((prev) => ({ ...prev, [pluginId]: !current }));
    try {
      const res = await fetch(`${API}/api/plugins/${pluginId}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'hud_toggle' }),
      });

      if (!res.ok) {
        throw new Error('Plugin toggle failed');
      }
    } catch {
      setPlugins((prev) => ({ ...prev, [pluginId]: current }));
    }
  };

  const emotion = EMOTIONS[emotionIdx];

  return (
    <div className="fixed right-0 top-0 bottom-0 w-64 z-50 flex flex-col"
      style={{ background: 'rgba(0,3,15,0.95)', backdropFilter: 'blur(20px)', borderLeft: '1px solid hsl(186 100% 50% / 0.3)', boxShadow: '-5px 0 30px hsl(186 100% 50% / 0.1)' }}>
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-hud-cyan/20">
        <div className="flex items-center gap-2">
          <Brain size={14} className="text-hud-cyan" />
          <span className="font-orbitron text-[10px] neon-text">AI PERSONALITY</span>
        </div>
        <button onClick={onClose} className="text-hud-cyan/40 hover:text-hud-cyan">
          <X size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scrollbar-hud p-3 flex flex-col gap-3">
        {/* Identity */}
        <div className="text-center p-3 hud-panel rounded">
          <div className="text-3xl mb-1" style={{ filter: `drop-shadow(0 0 8px ${emotion.color})` }}>{emotion.emoji}</div>
          <div className="font-orbitron text-xs neon-text font-bold">SPARK</div>
          <div className="font-mono-tech text-[9px] text-hud-cyan/50 mt-0.5">v4.1.7 · BUILD 20260219</div>
          <div className="font-orbitron text-[9px] mt-1" style={{ color: emotion.color }}>{emotion.label}</div>
        </div>

        {/* Memory */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1"><Cpu size={10} className="text-hud-cyan/60" /><span className="font-orbitron text-[8px] text-hud-cyan/60">MEMORY</span></div>
            <span className="font-orbitron text-[9px] text-hud-cyan">{memUsage}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-black/40">
            <div className="h-full rounded-full" style={{ width: `${memUsage}%`, background: '#00f5ff', boxShadow: '0 0 6px #00f5ff' }} />
          </div>
        </div>

        {/* Context */}
        <div>
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1"><Zap size={10} className="text-hud-amber/60" /><span className="font-orbitron text-[8px] text-hud-cyan/60">CONTEXT AWARENESS</span></div>
            <span className="font-orbitron text-[9px] text-hud-amber">{contextScore}%</span>
          </div>
          <div className="h-1.5 rounded-full bg-black/40">
            <div className="h-full rounded-full" style={{ width: `${contextScore}%`, background: '#ffb800', boxShadow: '0 0 6px #ffb800' }} />
          </div>
        </div>

        {/* KB Status */}
        <div className="flex flex-col gap-1 p-2 hud-panel rounded">
          <div className="flex items-center justify-between mb-1">
            <div className="flex items-center gap-1.5">
              <Database size={10} className="text-hud-blue" />
              <span className="font-orbitron text-[8px] text-hud-cyan/60">DEV OS GRAPH</span>
            </div>
            <span className="font-mono-tech text-[9px] text-hud-green">{devState.code_graph.nodes?.length || 0} NODES</span>
          </div>
          <div className="flex items-center justify-between border-t border-hud-cyan/10 pt-1 mt-1">
            <span className="font-orbitron text-[8px] text-hud-cyan/50">HEURISTICS ENGINE</span>
            <span className="font-mono-tech text-[8px] text-hud-cyan/70">v2.5.1</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="font-orbitron text-[8px] text-hud-cyan/50">CONTEXT TESTS</span>
            <span className="font-mono-tech text-[8px] text-hud-cyan/70">{Object.keys(devState.context_map.test_to_nodes || {}).length} MAPPED</span>
          </div>
        </div>

        {/* Learning mode */}
        <div className="flex items-center justify-between p-2 hud-panel rounded">
          <span className="font-orbitron text-[8px] text-hud-cyan/60">LEARNING MODE</span>
          <button onClick={() => setLearningMode(v => !v)}
            className={`w-8 h-4 rounded-full relative transition-all ${learningMode ? 'bg-hud-cyan/30' : 'bg-hud-cyan/10'}`}>
            <div className={`absolute top-0.5 w-3 h-3 rounded-full transition-all ${learningMode ? 'left-4 bg-hud-cyan' : 'left-0.5 bg-hud-cyan/30'}`} />
          </button>
        </div>

        {/* Uptime */}
        <div className="p-2 hud-panel rounded text-center">
          <div className="font-mono-tech text-[9px] text-hud-cyan/40 mb-0.5">
            {modelOnline ? 'MODEL ONLINE' : 'MODEL OFFLINE'}
          </div>
          <div className="font-orbitron text-sm neon-text">
            {avgLatencyMs !== null ? `${Math.round(avgLatencyMs)}ms` : (modelOnline ? 'WARM' : '—')}
          </div>
          <div className="font-mono-tech text-[8px] text-hud-cyan/45 mt-1">
            {activeModel || 'unknown'}
            {avgLatencyMs !== null ? ' · avg' : ''}
          </div>
        </div>

        {/* Plugins */}
        <div>
          <div className="font-orbitron text-[8px] text-hud-cyan/60 mb-1.5">ACTIVE PLUGINS</div>
          <div className="flex flex-col gap-1">
            {PLUGINS.map((pl) => {
              const active = !!plugins[pl.id];
              return (
                <div key={pl.id} className="flex items-center justify-between px-2 py-1 rounded border border-hud-cyan/15">
                  <span className="font-orbitron text-[8px] text-hud-cyan/70">{pl.name}</span>
                  <button onClick={() => togglePlugin(pl.id)}
                    className={`w-6 h-3 rounded-full relative transition-all ${active ? 'bg-hud-cyan/40' : 'bg-hud-cyan/10'}`}>
                    <div className={`absolute top-0.5 w-2 h-2 rounded-full transition-all ${active ? 'left-3.5 bg-hud-cyan' : 'left-0.5 bg-hud-cyan/30'}`} />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
