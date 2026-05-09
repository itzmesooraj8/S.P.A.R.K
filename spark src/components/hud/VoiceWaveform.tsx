import React, { useEffect, useRef } from 'react';
import { useSparkStore } from '../../store/sparkStore';

export function VoiceWaveform() {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const voiceState = useSparkStore(state => state.voiceState);
  const activeTheme = useSparkStore(state => state.activeTheme);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    let animationId: number;
    let phase = 0;

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      if (voiceState === 'idle') {
        // Flat line
        ctx.beginPath();
        ctx.moveTo(0, canvas.height / 2);
        ctx.lineTo(canvas.width, canvas.height / 2);
        ctx.strokeStyle = activeTheme === 'cyan' ? '#00f5ff' : 
                          activeTheme === 'red' ? '#ff2a2a' : 
                          activeTheme === 'amber' ? '#ffb000' : '#ffffff';
        ctx.lineWidth = 2;
        ctx.stroke();
      } else {
        // Animated waveform
        ctx.beginPath();
        ctx.moveTo(0, canvas.height / 2);
        
        const bars = 40;
        const barWidth = canvas.width / bars;
        
        for (let i = 0; i < bars; i++) {
          const x = i * barWidth;
          const noise = Math.sin(phase + i * 0.5) * Math.cos(phase * 1.2 + i * 0.2);
          const amplitude = voiceState === 'speaking' ? 30 : 
                            voiceState === 'listening' ? 15 : 5;
          
          const h = (noise * amplitude) + (Math.random() * (voiceState === 'processing' ? 10 : 2));
          
          ctx.lineTo(x, canvas.height / 2 + h);
        }
        
        ctx.strokeStyle = activeTheme === 'cyan' ? '#00f5ff' : 
                          activeTheme === 'red' ? '#ff2a2a' : 
                          activeTheme === 'amber' ? '#ffb000' : '#ffffff';
        ctx.lineWidth = 3;
        ctx.shadowBlur = 10;
        ctx.shadowColor = ctx.strokeStyle;
        ctx.stroke();
        
        phase += 0.15;
      }
      
      animationId = requestAnimationFrame(render);
    };

    render();

    return () => cancelAnimationFrame(animationId);
  }, [voiceState, activeTheme]);

  return (
    <div className="relative overflow-hidden hud-panel-glow p-4 flex flex-col items-center justify-center min-h-[140px] rounded-xl">
      <div className="absolute inset-0 pointer-events-none" style={{ background: 'radial-gradient(circle at center, rgba(0,245,255,0.10) 0%, transparent 55%)' }} />
      <div className="absolute inset-x-8 top-8 h-px bg-gradient-to-r from-transparent via-cyan-300/70 to-transparent" />
      <div className={`relative z-10 text-[10px] mb-3 uppercase tracking-[0.35em] ${
        voiceState === 'idle' ? 'text-white/35' : `neon-text-${activeTheme}`
      }`}>
        {voiceState === 'idle' ? 'MIC STANDBY' : 
         voiceState === 'listening' ? 'OBSERVING INPUT' :
         voiceState === 'processing' ? 'ORIENTING LOGIC' : 'ACTING'}
      </div>
      <canvas 
        ref={canvasRef} 
        width={360} 
        height={84} 
        className="relative z-10 w-full max-w-[360px]"
      />
      <div className="relative z-10 mt-3 flex items-center gap-1.5 opacity-60">
        {new Array(10).fill(0).map((_, index) => (
          <span
            key={index}
            className="w-1 rounded-full"
            style={{
              height: `${6 + ((index % 4) * 4)}px`,
              background: voiceState === 'idle' ? 'rgba(255,255,255,0.16)' : 'rgba(0,245,255,0.65)',
              animation: 'waveform 1.2s ease-in-out infinite',
              animationDelay: `${index * 0.08}s`,
            }}
          />
        ))}
      </div>
    </div>
  );
}
