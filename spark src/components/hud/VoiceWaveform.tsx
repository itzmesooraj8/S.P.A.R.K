import React, { useEffect, useRef } from 'react';

interface Props {
  amplitude: number[]; // Array of normalized amplitudes (0 to 1)
  color?: string;
  width?: number;
  height?: number;
  barWidth?: number;
  gap?: number;
}

export default function VoiceWaveform({ 
  amplitude, 
  color = '#00E5FF', 
  width = 240, 
  height = 60,
  barWidth = 3,
  gap = 3
}: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, width, height);

    const centerY = height / 2;
    const numBars = Math.min(amplitude.length, Math.floor(width / (barWidth + gap)));
    const totalContentWidth = numBars * (barWidth + gap) - gap;
    const startX = (width - totalContentWidth) / 2;

    for (let i = 0; i < numBars; i++) {
      const amp = amplitude[i] || 0.05; // Base height of 5%
      // Map amp (0 to 1) to bar height (min 2, max height * 0.9)
      let barHeight = Math.max(2, amp * height * 0.9);
      
      // Ensure smooth corners
      ctx.lineCap = 'round';
      ctx.lineWidth = barWidth;

      // Create gradient for the bar
      const gradient = ctx.createLinearGradient(0, centerY - barHeight/2, 0, centerY + barHeight/2);
      gradient.addColorStop(0, `${color}20`);
      gradient.addColorStop(0.5, color);
      gradient.addColorStop(1, `${color}20`);

      ctx.strokeStyle = gradient;

      const x = startX + i * (barWidth + gap);
      
      // Draw the bar
      ctx.beginPath();
      ctx.moveTo(x + barWidth/2, centerY - barHeight/2);
      ctx.lineTo(x + barWidth/2, centerY + barHeight/2);
      ctx.stroke();

      // Add a subtle glow
      ctx.shadowColor = color;
      ctx.shadowBlur = amp > 0.3 ? 10 : 0;
    }

    // Reset shadow for next frame
    ctx.shadowBlur = 0;

  }, [amplitude, color, width, height, barWidth, gap]);

  return (
    <div className="relative flex items-center justify-center py-2">
      <div className="absolute inset-0 bg-gradient-to-r from-transparent via-cyan-500/10 to-transparent blur-md rounded-full" />
      <canvas 
        ref={canvasRef} 
        width={width} 
        height={height} 
        className="relative z-10 w-full max-w-full"
      />
    </div>
  );
}
