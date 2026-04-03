import { AiStatus } from '@/hooks/useVoiceEngine';
import { Mic, MicOff, Brain, AlertTriangle } from 'lucide-react';
import { useCombatStore } from '@/store/useCombatStore';
import { useEffect, useCallback, useState } from 'react';

interface Props {
  status: AiStatus;
  isListening: boolean;
  amplitude: number[];
  onToggleMic: () => void;
  aiMode: string;
}

const STATUS_CONFIG: Record<string, { color: string; label: string; rings: number }> = {
  idle:        { color: '#00f5ff', label: 'IDLE',       rings: 1 },
  listening:   { color: '#00ff88', label: 'LISTENING',  rings: 2 },
  thinking:    { color: '#ffb800', label: 'PROCESSING', rings: 3 },
  responding:  { color: '#0066ff', label: 'RESPONDING', rings: 2 },
  combat:      { color: '#FF2D55', label: 'COMBAT',     rings: 3 },
  degraded:    { color: '#FF9F0A', label: 'DEGRADED',   rings: 1 },
};

export default function CoreModule({ status, isListening, amplitude, onToggleMic, aiMode }: Props) {
  const combatActive = useCombatStore(s => s.isActive)
  const { sessionToken } = useCombatStore()
  const [briefing, setBriefing] = useState<string | null>(null)
  const [briefingLoading, setBriefingLoading] = useState(false)

  // Effective display status — override with 'combat' when in combat mode
  const effectiveStatus = combatActive ? 'combat' : status
  const cfg = STATUS_CONFIG[effectiveStatus] ?? STATUS_CONFIG.idle

  const fetchBriefing = useCallback(async () => {
    if (!combatActive || !sessionToken) return
    setBriefingLoading(true)
    try {
      const res = await fetch(
        `${window.location.protocol}//${window.location.hostname}:8000/api/combat/spark/briefing`,
        {
          method:  'POST',
          headers: { 'Content-Type': 'application/json', 'X-Combat-Token': sessionToken },
          body:    JSON.stringify({ mode: aiMode, speak: false, context: { combat_active: true } }),
        },
      )
      if (res.ok) {
        const data = await res.json()
        setBriefing(data.text || null)
      }
    } catch { /* ignore */ }
    finally { setBriefingLoading(false) }
  }, [combatActive, sessionToken, aiMode])

  // Fetch briefing when combat activates
  useEffect(() => {
    if (combatActive) {
      fetchBriefing()
    } else {
      setBriefing(null)
    }
  }, [combatActive])

  const size = 260;
  const cx = size / 2;
  const cy = size / 2;

  return (
    <div className="flex flex-col items-center justify-center h-full gap-3">
      {/* Wake word indicator */}
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${status === 'idle' ? 'bg-hud-cyan/60 animate-pulse' : 'bg-hud-green animate-pulse'}`} />
        <span className="font-orbitron text-[10px] tracking-widest neon-text animate-flicker">
          SPARK ONLINE
        </span>
        <div className={`w-2 h-2 rounded-full ${status === 'idle' ? 'bg-hud-cyan/60 animate-pulse' : 'bg-hud-green animate-pulse'}`} />
      </div>

      {/* Core SVG */}
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="absolute inset-0">
          {/* Background circles */}
          {[120, 105, 90, 75, 60].map((r, i) => (
            <circle key={i} cx={cx} cy={cy} r={r}
              fill="none"
              stroke={cfg.color}
              strokeWidth={i === 0 ? 0.5 : 0.3}
              opacity={0.1 + i * 0.04}
            />
          ))}

          {/* Radar grid lines */}
          {[0, 30, 60, 90, 120, 150].map(angle => (
            <line key={angle}
              x1={cx} y1={cy - 120}
              x2={cx} y2={cy + 120}
              stroke={cfg.color}
              strokeWidth={0.3}
              opacity={0.1}
              transform={`rotate(${angle} ${cx} ${cy})`}
            />
          ))}

          {/* Outer rotating ring 1 - slow CW */}
          <circle cx={cx} cy={cy} r={118} fill="none" stroke={cfg.color} strokeWidth={1.5}
            strokeDasharray="12 8" opacity={0.5}
            className="animate-rotate-cw-slow" style={{ transformOrigin: `${cx}px ${cy}px` }}
          />

          {/* Outer decorative arcs */}
          <path
            d={`M ${cx - 118} ${cy} A 118 118 0 0 1 ${cx} ${cy - 118}`}
            fill="none" stroke={cfg.color} strokeWidth={3} opacity={0.4}
            className="animate-rotate-cw-slow" style={{ transformOrigin: `${cx}px ${cy}px` }}
          />
          <path
            d={`M ${cx + 118} ${cy} A 118 118 0 0 1 ${cx} ${cy + 118}`}
            fill="none" stroke={cfg.color} strokeWidth={3} opacity={0.4}
            className="animate-rotate-cw-slow" style={{ transformOrigin: `${cx}px ${cy}px` }}
          />

          {/* Mid rotating ring - medium CCW */}
          <circle cx={cx} cy={cy} r={95} fill="none" stroke={cfg.color} strokeWidth={1}
            strokeDasharray="4 12" opacity={0.6}
            className="animate-rotate-ccw-med" style={{ transformOrigin: `${cx}px ${cy}px` }}
          />

          {/* Tick marks on mid ring */}
          {Array.from({ length: 24 }, (_, i) => {
            const a = (i / 24) * Math.PI * 2;
            const r1 = 90, r2 = 100;
            return (
              <line key={i}
                x1={cx + Math.cos(a) * r1} y1={cy + Math.sin(a) * r1}
                x2={cx + Math.cos(a) * r2} y2={cy + Math.sin(a) * r2}
                stroke={cfg.color} strokeWidth={i % 6 === 0 ? 2 : 0.8}
                opacity={i % 6 === 0 ? 0.8 : 0.3}
              />
            );
          })}

          {/* Inner rotating ring - fast CW */}
          <circle cx={cx} cy={cy} r={72} fill="none" stroke={cfg.color} strokeWidth={1.5}
            strokeDasharray="20 5" opacity={0.7}
            className="animate-rotate-cw-fast" style={{ transformOrigin: `${cx}px ${cy}px` }}
          />

          {/* Radar sweep */}
          <defs>
            <radialGradient id="radarGrad" cx="0%" cy="50%" r="100%">
              <stop offset="0%" stopColor={cfg.color} stopOpacity="0.6" />
              <stop offset="100%" stopColor={cfg.color} stopOpacity="0" />
            </radialGradient>
          </defs>
          <path
            d={`M ${cx} ${cy} L ${cx + 70} ${cy} A 70 70 0 0 1 ${cx + 70 * Math.cos(Math.PI / 3)} ${cy + 70 * Math.sin(Math.PI / 3)} Z`}
            fill="url(#radarGrad)"
            className="animate-radar"
            style={{ transformOrigin: `${cx}px ${cy}px` }}
            opacity={0.6}
          />

          {/* Core circle */}
          <circle cx={cx} cy={cy} r={50}
            fill={`${cfg.color}18`}
            stroke={cfg.color}
            strokeWidth={2}
            opacity={1}
          />
          <circle cx={cx} cy={cy} r={50}
            fill="none"
            stroke={cfg.color}
            strokeWidth={4}
            opacity={effectiveStatus !== 'idle' ? 0.6 : 0.3}
            style={{ filter: `drop-shadow(0 0 8px ${cfg.color})` }}
          />

          {/* Inner glow */}
          <circle cx={cx} cy={cy} r={45}
            fill={`${cfg.color}08`}
            stroke={cfg.color}
            strokeWidth={0.5}
            opacity={0.6}
          />

          {/* Waveform bars around core */}
          {amplitude.map((amp, i) => {
            const angle = (i / 32) * Math.PI * 2 - Math.PI / 2;
            const innerR = 55;
            const barH = amp * 25 + 3;
            const outerR = innerR + barH;
            return (
              <line key={i}
                x1={cx + Math.cos(angle) * innerR}
                y1={cy + Math.sin(angle) * innerR}
                x2={cx + Math.cos(angle) * outerR}
                y2={cy + Math.sin(angle) * outerR}
                stroke={cfg.color}
                strokeWidth={2.5}
                opacity={0.5 + amp * 0.5}
                style={{ filter: amp > 0.5 ? `drop-shadow(0 0 3px ${cfg.color})` : 'none' }}
              />
            );
          })}

          {/* Corner decorations */}
          {[[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([sx, sy], i) => (
            <g key={i}>
              <line
                x1={cx + sx * 130} y1={cy + sy * 110}
                x2={cx + sx * 130} y2={cy + sy * 130}
                stroke={cfg.color} strokeWidth={2} opacity={0.5}
              />
              <line
                x1={cx + sx * 110} y1={cy + sy * 130}
                x2={cx + sx * 130} y2={cy + sy * 130}
                stroke={cfg.color} strokeWidth={2} opacity={0.5}
              />
            </g>
          ))}
        </svg>

        {/* Center content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          {combatActive
            ? <AlertTriangle size={20} style={{ color: cfg.color, filter: `drop-shadow(0 0 6px ${cfg.color})` }} />
            : <Brain size={20} style={{ color: cfg.color, filter: `drop-shadow(0 0 6px ${cfg.color})` }} />
          }
          <div className="font-orbitron text-[9px] mt-1 tracking-widest"
            style={{ color: cfg.color, textShadow: `0 0 8px ${cfg.color}` }}>
            {cfg.label}
          </div>
          <div className="font-rajdhani text-[8px] text-hud-cyan/50 mt-0.5">{aiMode} MODE</div>
        </div>
      </div>

      {/* Mic button */}
      <button
        onClick={onToggleMic}
        className={`relative flex items-center gap-2 px-5 py-2 rounded border font-orbitron text-xs tracking-widest transition-all duration-200 ${isListening
            ? 'border-hud-green text-hud-green bg-hud-green/10'
            : 'border-hud-cyan/50 text-hud-cyan hover:border-hud-cyan hover:bg-hud-cyan/10'
          }`}
        style={{
          boxShadow: isListening
            ? '0 0 15px hsl(145 100% 45% / 0.4)'
            : '0 0 8px hsl(186 100% 50% / 0.2)',
        }}
      >
        {isListening ? (
          <>
            <MicOff size={14} />
            <span>STOP LISTENING</span>
            <div className="absolute inset-0 rounded animate-pulse-ring border border-hud-green opacity-30" />
          </>
        ) : (
          <>
            <Mic size={14} />
            <span>ACTIVATE MIC</span>
          </>
        )}
      </button>

      {/* Status bar */}
      <div className="flex gap-3">
        {(['idle', 'listening', 'thinking', 'responding', ...(combatActive ? ['combat'] : [])] as string[]).map(s => (
          <div key={s} className="flex flex-col items-center gap-0.5">
            <div className={`w-1.5 h-1.5 rounded-full transition-all duration-300 ${effectiveStatus === s ? 'scale-125' : 'opacity-30'
              }`} style={{
                background: STATUS_CONFIG[s]?.color ?? '#555',
                boxShadow: effectiveStatus === s ? `0 0 6px ${STATUS_CONFIG[s]?.color}` : 'none',
              }} />
            <span className="font-mono-tech text-[7px] text-hud-cyan/40">{s.toUpperCase()}</span>
          </div>
        ))}
      </div>

      {/* SPARK briefing strip */}
      {combatActive && (
        <div style={{
          maxWidth: 280, textAlign: 'center', color: '#FF9F0A',
          fontSize: 10, fontStyle: 'italic', lineHeight: 1.4, minHeight: 32,
        }}>
          {briefingLoading ? (
            <span style={{ color: '#3a1520' }}>Generating briefing…</span>
          ) : briefing ? (
            <>
              <span style={{ color: '#555', fontSize: 9 }}>SPARK: </span>
              {briefing}
            </>
          ) : (
            <button onClick={fetchBriefing}
              style={{ background: 'transparent', border: '1px solid #3a1520',
                borderRadius: 4, padding: '2px 10px', color: '#555', fontSize: 9, cursor: 'pointer' }}>
              GET BRIEFING
            </button>
          )}
        </div>
      )}
    </div>
  );
}
