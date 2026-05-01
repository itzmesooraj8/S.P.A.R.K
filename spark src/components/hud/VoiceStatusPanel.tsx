import { useEffect, useMemo, useState } from 'react';
import { Mic, Volume2, Activity, SlidersHorizontal, Cpu } from 'lucide-react';
import type { TtsPlaybackState } from '@/hooks/useVoiceEngine';

const API = import.meta.env.VITE_API_BASE ?? 'http://localhost:8000';

interface BackendVoiceStatus {
  running: boolean;
  phase: string;
  queue_depth: number;
  wake_sensitivity: number;
  tts_progress: number;
  last_transcript: string;
  last_reply: string;
  last_error: string;
  last_tts_engine: string;
}

interface ModelItem {
  name: string;
  provider: string;
  available: boolean;
}

interface ModelsStatus {
  models: ModelItem[];
}

interface ActiveModel {
  model: string;
}

interface VoiceEngineStatus {
  active?: string;
}

interface Props {
  status: string;
  isListening: boolean;
  amplitude: number[];
  ttsPlayback: TtsPlaybackState;
}

export default function VoiceStatusPanel({ status, isListening, amplitude, ttsPlayback }: Props) {
  const [backendStatus, setBackendStatus] = useState<BackendVoiceStatus | null>(null);
  const [activeEngine, setActiveEngine] = useState<string>('');
  const [models, setModels] = useState<ModelItem[]>([]);
  const [activeModel, setActiveModel] = useState<string>('');
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [wakeSensitivity, setWakeSensitivity] = useState<number>(0.5);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    const refresh = async () => {
      try {
        const [voiceRes, engineRes, modelRes, activeRes] = await Promise.all([
          fetch(`${API}/api/voice/status`),
          fetch(`${API}/api/voice/engine`),
          fetch(`${API}/api/models/status`),
          fetch(`${API}/api/models/active`),
        ]);

        if (!voiceRes.ok || !modelRes.ok || !activeRes.ok) {
          return;
        }

        const voiceData = (await voiceRes.json()) as BackendVoiceStatus;
        const engineData = engineRes.ok ? (await engineRes.json()) as VoiceEngineStatus : null;
        const modelData = (await modelRes.json()) as ModelsStatus;
        const activeData = (await activeRes.json()) as ActiveModel;

        if (cancelled) return;

        setBackendStatus(voiceData);
        setActiveEngine((engineData?.active || '').trim());
        setWakeSensitivity(Number(voiceData.wake_sensitivity ?? 0.5));
        setModels(modelData.models ?? []);
        setActiveModel(activeData.model ?? '');
        setSelectedModel((prev) => prev || activeData.model || '');
      } catch {
        // keep silent; panel should stay resilient while backend reconnects
      }
    };

    refresh();
    const timer = window.setInterval(refresh, 2500);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const localModels = useMemo(
    () => models.filter((m) => m.provider === 'ollama' && m.available).map((m) => m.name),
    [models],
  );

  const saveSensitivity = async () => {
    setPending(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/voice/wakeword/sensitivity`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: wakeSensitivity }),
      });
      if (!res.ok) {
        throw new Error('Failed to save wake sensitivity');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save sensitivity');
    } finally {
      setPending(false);
    }
  };

  const switchModel = async () => {
    if (!selectedModel || selectedModel === activeModel) return;
    setPending(true);
    setError('');
    try {
      const res = await fetch(`${API}/api/models/active`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model: selectedModel }),
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || 'Failed to switch model');
      }
      setActiveModel(selectedModel);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to switch model');
    } finally {
      setPending(false);
    }
  };

  const ttsPct = Math.round((ttsPlayback.progress || 0) * 100);
  const backendTtsPct = Math.round((backendStatus?.tts_progress || 0) * 100);
  const displayEngine = useMemo(() => {
    const playbackEngine = (ttsPlayback.engine || '').trim();
    if (playbackEngine && playbackEngine.toLowerCase() !== 'unknown') {
      return playbackEngine;
    }

    const lastEngine = (backendStatus?.last_tts_engine || '').trim();
    if (lastEngine) {
      return lastEngine;
    }

    return activeEngine || 'unknown';
  }, [activeEngine, backendStatus?.last_tts_engine, ttsPlayback.engine]);

  return (
    <div className="h-full flex flex-col gap-2 p-2 overflow-y-auto scrollbar-hud animate-boot-right" style={{ animationDelay: '0.2s' }}>
      <div className="flex items-center justify-between pb-1 border-b border-hud-cyan/20">
        <span className="font-orbitron text-[9px] tracking-widest neon-text">VOICE STATUS</span>
        <span className="font-mono-tech text-[8px] text-hud-cyan/60">{backendStatus?.phase?.toUpperCase() || 'IDLE'}</span>
      </div>

      <div className="grid grid-cols-2 gap-1.5">
        <div className="p-1.5 rounded border border-hud-cyan/20 bg-black/30">
          <div className="flex items-center gap-1">
            <Mic size={10} className={isListening ? 'text-hud-green' : 'text-hud-cyan/50'} />
            <span className="font-orbitron text-[8px] text-hud-cyan/70">MIC</span>
          </div>
          <div className="font-mono-tech text-[8px] mt-1" style={{ color: isListening ? '#30d158' : '#8aa' }}>
            {status.toUpperCase()}
          </div>
        </div>

        <div className="p-1.5 rounded border border-hud-cyan/20 bg-black/30">
          <div className="flex items-center gap-1">
            <Activity size={10} className={backendStatus?.running ? 'text-hud-green' : 'text-hud-red/70'} />
            <span className="font-orbitron text-[8px] text-hud-cyan/70">WAKE LOOP</span>
          </div>
          <div className="font-mono-tech text-[8px] mt-1" style={{ color: backendStatus?.running ? '#30d158' : '#ff453a' }}>
            {backendStatus?.running ? 'ONLINE' : 'OFFLINE'}
          </div>
        </div>
      </div>

      <div className="p-1.5 rounded border border-hud-cyan/20 bg-black/35">
        <div className="flex items-center gap-1 mb-1">
          <Volume2 size={10} className={ttsPlayback.speaking ? 'text-hud-amber' : 'text-hud-cyan/50'} />
          <span className="font-orbitron text-[8px] text-hud-cyan/70">TTS PLAYBACK</span>
          <span className="ml-auto font-mono-tech text-[8px] text-hud-cyan/50">
            {ttsPlayback.speaking ? `${ttsPct}%` : `${backendTtsPct}%`}
          </span>
        </div>
        <div className="h-1.5 rounded bg-hud-cyan/10 overflow-hidden">
          <div
            className="h-full rounded transition-all duration-150"
            style={{
              width: `${ttsPlayback.speaking ? ttsPct : backendTtsPct}%`,
              background: ttsPlayback.speaking ? '#ffb800' : '#00f5ff',
              boxShadow: ttsPlayback.speaking ? '0 0 8px #ffb800' : '0 0 6px #00f5ff',
            }}
          />
        </div>
        <div className="font-mono-tech text-[7px] text-hud-cyan/45 mt-1">
          Engine: {displayEngine}
        </div>
      </div>

      <div className="p-1.5 rounded border border-hud-cyan/20 bg-black/35">
        <div className="flex items-center gap-1 mb-1">
          <Mic size={10} className="text-hud-cyan/70" />
          <span className="font-orbitron text-[8px] text-hud-cyan/70">LISTENING WAVE</span>
        </div>
        <div className="flex items-end gap-[2px] h-6">
          {new Array(16).fill(0).map((_, idx) => {
            const val = amplitude[idx] ?? 0;
            const height = Math.max(2, Math.round(val * 24));
            return (
              <div
                key={idx}
                className="w-[4px] rounded-sm transition-all duration-75"
                style={{
                  height,
                  background: isListening ? '#30d158' : '#00f5ff55',
                  boxShadow: isListening ? '0 0 6px #30d158' : 'none',
                }}
              />
            );
          })}
        </div>
      </div>

      <div className="p-1.5 rounded border border-hud-cyan/20 bg-black/35">
        <div className="flex items-center gap-1 mb-1">
          <SlidersHorizontal size={10} className="text-hud-cyan/70" />
          <span className="font-orbitron text-[8px] text-hud-cyan/70">WAKE SENSITIVITY</span>
          <span className="ml-auto font-mono-tech text-[8px] text-hud-cyan/60">{wakeSensitivity.toFixed(2)}</span>
        </div>
        <input
          type="range"
          min={0.1}
          max={0.95}
          step={0.01}
          value={wakeSensitivity}
          onChange={(e) => setWakeSensitivity(Number(e.target.value))}
          className="w-full accent-cyan-400"
        />
        <button
          onClick={saveSensitivity}
          disabled={pending}
          className="mt-1 w-full font-orbitron text-[8px] px-2 py-1 rounded border border-hud-cyan/30 text-hud-cyan/70 hover:border-hud-cyan/70 transition-colors disabled:opacity-40"
        >
          SAVE SENSITIVITY
        </button>
      </div>

      <div className="p-1.5 rounded border border-hud-cyan/20 bg-black/35">
        <div className="flex items-center gap-1 mb-1">
          <Cpu size={10} className="text-hud-cyan/70" />
          <span className="font-orbitron text-[8px] text-hud-cyan/70">ACTIVE MODEL</span>
        </div>
        <select
          value={selectedModel}
          onChange={(e) => setSelectedModel(e.target.value)}
          className="w-full bg-transparent border border-hud-cyan/20 rounded px-2 py-1 font-mono-tech text-[8px] text-hud-cyan outline-none"
        >
          {localModels.length === 0 && <option className="bg-black">NO LOCAL MODELS</option>}
          {localModels.map((model) => (
            <option key={model} value={model} className="bg-black">
              {model}
            </option>
          ))}
        </select>
        <div className="font-mono-tech text-[7px] text-hud-cyan/45 mt-1">Current: {activeModel || 'unknown'}</div>
        <button
          onClick={switchModel}
          disabled={pending || !selectedModel || selectedModel === activeModel}
          className="mt-1 w-full font-orbitron text-[8px] px-2 py-1 rounded border border-hud-cyan/30 text-hud-cyan/70 hover:border-hud-cyan/70 transition-colors disabled:opacity-40"
        >
          SWITCH MODEL
        </button>
      </div>

      {error && (
        <div className="p-1.5 rounded border border-hud-red/40 bg-hud-red/10 font-mono-tech text-[8px] text-hud-red/80">
          {error}
        </div>
      )}

      {backendStatus?.last_error && (
        <div className="p-1.5 rounded border border-hud-amber/40 bg-hud-amber/10 font-mono-tech text-[8px] text-hud-amber/90">
          {backendStatus.last_error}
        </div>
      )}
    </div>
  );
}
