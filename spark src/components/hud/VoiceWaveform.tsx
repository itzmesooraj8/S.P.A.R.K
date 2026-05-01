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
    <div className="hud-panel p-4 flex flex-col items-center justify-center min-h-[120px]">
      <div className={`text-xs mb-2 uppercase tracking-widest ${
        voiceState === 'idle' ? 'text-gray-500' : `neon-text-${activeTheme}`
      }`}>
        {voiceState === 'idle' ? 'MIC STANDBY' : 
         voiceState === 'listening' ? 'OBSERVING INPUT' :
         voiceState === 'processing' ? 'ORIENTING LOGIC' : 'ACTING'}
      </div>
      <canvas 
        ref={canvasRef} 
        width={300} 
        height={60} 
        className="w-full max-w-[300px]"
      />
    </div>
  );
}
