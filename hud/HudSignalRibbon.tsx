import { useMemo } from 'react';
import { Activity, BrainCircuit, Mic, Radar, Sparkles } from 'lucide-react';

type HudPhase = 'idle' | 'listening' | 'thinking' | 'responding' | 'speaking' | 'executing' | 'combat';

type Props = {
  phase: HudPhase;
  aiMode: string;
  hudMode: 'normal' | 'developer';
  isListening: boolean;
  ttsSpeaking: boolean;
};

const PHASE_META: Record<HudPhase, { label: string; description: string; icon: React.ComponentType<{ size?: number }> }> = {
  idle: { label: 'IDLE', description: 'ambient awareness', icon: Radar },
  listening: { label: 'LISTENING', description: 'capturing intent', icon: Mic },
  thinking: { label: 'THINKING', description: 'synthesizing context', icon: BrainCircuit },
  responding: { label: 'RESPONDING', description: 'composing output', icon: Sparkles },
  speaking: { label: 'SPEAKING', description: 'audio output active', icon: Activity },
  executing: { label: 'EXECUTING', description: 'tool chain in motion', icon: Activity },
  combat: { label: 'COMBAT', description: 'tactical posture engaged', icon: Activity },
};

export default function HudSignalRibbon({ phase, aiMode, hudMode, isListening, ttsSpeaking }: Props) {
  const meta = PHASE_META[phase];
  const ActiveIcon = meta.icon;

  const chips = useMemo(() => ([
    { label: aiMode, tone: 'cyan' },
    { label: hudMode === 'developer' ? 'DEVELOPER VIEW' : 'FOCUSED VIEW', tone: hudMode === 'developer' ? 'cyan' : 'white' },
    { label: isListening ? 'MIC HOT' : 'MIC ARMED', tone: isListening ? 'green' : 'white' },
    { label: ttsSpeaking ? 'VOICE LIVE' : 'VOICE QUIET', tone: ttsSpeaking ? 'cyan' : 'white' },
  ]), [aiMode, hudMode, isListening, ttsSpeaking]);

  return (
    <div className="mx-1.5 mt-1.5 rounded-2xl border border-white/8 bg-black/30 backdrop-blur-xl px-3 py-2 shadow-[0_0_30px_rgba(0,245,255,0.06)]">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 min-w-0">
          <div className="flex h-8 w-8 items-center justify-center rounded-full border border-cyan-300/20 bg-cyan-400/10 text-cyan-100 shadow-[0_0_18px_rgba(0,245,255,0.08)]">
            <ActiveIcon size={14} />
          </div>
          <div className="min-w-0">
            <div className="text-[10px] uppercase tracking-[0.38em] text-cyan-50/85 font-orbitron">{meta.label}</div>
            <div className="text-[8px] uppercase tracking-[0.3em] text-white/40 font-mono-tech">{meta.description}</div>
          </div>
        </div>

        <div className="hidden md:block flex-1 h-px bg-gradient-to-r from-transparent via-cyan-300/30 to-transparent" />

        <div className="flex flex-wrap items-center gap-1.5 ml-auto">
          {chips.map((chip) => (
            <span
              key={chip.label}
              className="rounded-full border px-2 py-0.5 text-[8px] uppercase tracking-[0.28em] font-orbitron"
              style={{
                borderColor: chip.tone === 'cyan' ? 'rgba(0,245,255,0.2)' : 'rgba(255,255,255,0.12)',
                background: chip.tone === 'cyan' ? 'rgba(0,245,255,0.08)' : 'rgba(255,255,255,0.03)',
                color: chip.tone === 'cyan' ? '#dffcff' : 'rgba(255,255,255,0.62)',
              }}
            >
              {chip.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
