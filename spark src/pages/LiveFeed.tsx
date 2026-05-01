import React from 'react';
import { AgentLog } from '../components/hud/AgentLog';
import { VoiceWaveform } from '../components/hud/VoiceWaveform';
import { SysMetrics } from '../components/hud/SysMetrics';
import { PortfolioTicker } from '../components/hud/PortfolioTicker';
import { ReminderOverlay } from '../components/hud/ReminderOverlay';

export default function LiveFeed() {
  return (
    <div className="w-full h-screen bg-[#010812] text-white p-4 font-mono overflow-hidden relative">
      <ReminderOverlay />
      
      {/* Decorative corners */}
      <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-cyan-500 opacity-50 m-2" />
      <div className="absolute top-0 right-0 w-8 h-8 border-t-2 border-r-2 border-cyan-500 opacity-50 m-2" />
      <div className="absolute bottom-0 left-0 w-8 h-8 border-b-2 border-l-2 border-cyan-500 opacity-50 m-2" />
      <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-cyan-500 opacity-50 m-2" />

      {/* Scan line effect */}
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] z-50 opacity-20" />

      <div className="flex flex-col h-full gap-4 relative z-10">
        
        {/* Header */}
        <div className="flex justify-between items-end border-b border-cyan-500/30 pb-2">
          <div>
            <h1 className="text-2xl font-bold uppercase tracking-[0.3em] neon-text-cyan font-['Orbitron']">
              S.P.A.R.K. LIVE FEED
            </h1>
            <div className="text-[10px] text-cyan-500/70 tracking-widest uppercase">
              Operational Session HUD • Real-Time Uplink
            </div>
          </div>
          <div className="text-right text-xs text-cyan-400 font-mono flex gap-4">
            <span className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              WS_CONNECTED
            </span>
            <span>{new Date().toISOString().split('T')[1].slice(0, 8)}</span>
          </div>
        </div>

        {/* 3-Column Layout */}
        <div className="grid grid-cols-12 gap-4 flex-1 min-h-0">
          
          {/* Left Column - Agent Log */}
          <div className="col-span-3 h-full">
            <AgentLog />
          </div>

          {/* Center Column - Voice & Main Focus */}
          <div className="col-span-6 flex flex-col gap-4 h-full">
            <div className="h-[200px] shrink-0">
              <VoiceWaveform />
            </div>
            
            <div className="flex-1 hud-panel p-4 flex flex-col justify-end bg-gradient-to-t from-[#00f5ff0a] to-transparent">
              <div className="text-[10px] uppercase text-cyan-500/50 tracking-widest mb-4">
                RECENT EXCHANGES
              </div>
              <div className="flex flex-col gap-4 overflow-y-auto no-scrollbar">
                {/* Simulated recent exchanges for layout structure. In reality, would pull from a store. */}
                <div className="opacity-40">
                  <span className="text-gray-500 block text-xs mb-1">USER</span>
                  <span className="text-gray-300">Start the morning protocol.</span>
                </div>
                <div className="opacity-60">
                  <span className="text-cyan-500 block text-xs mb-1">SPARK</span>
                  <span className="text-cyan-100">Good morning, sir. All systems are nominal...</span>
                </div>
                <div>
                  <span className="text-gray-500 block text-xs mb-1">USER</span>
                  <span className="text-gray-300">What's my portfolio looking like today?</span>
                </div>
              </div>
            </div>
          </div>

          {/* Right Column - Telemetry & Markets */}
          <div className="col-span-3 flex flex-col gap-4 h-full">
            <div className="flex-none">
              <SysMetrics />
            </div>
            <div className="flex-1 min-h-0">
              <PortfolioTicker />
            </div>
            
            {/* Quick Data Panel */}
            <div className="hud-panel p-4 text-xs font-mono h-32 flex flex-col justify-center">
              <div className="flex justify-between items-center text-gray-400 mb-2">
                <span>LOCAL_ENV</span>
                <span className="text-amber-400">SYNCED</span>
              </div>
              <div className="text-cyan-300">WEATHER: 34°C, Clear</div>
              <div className="text-cyan-300 mt-1">LAT/LNG: 10.78° N, 76.65° E</div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
