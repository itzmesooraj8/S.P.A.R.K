import React, { useState, useEffect, useRef } from 'react';
import { usePersonalAISocket } from '@/hooks/usePersonalAISocket';
import { VoiceWaveform } from '../components/hud/VoiceWaveform';

export default function PersonalAI() {
  const { messages, isConnected, activityLogs, sendToBrain, logActivity } = usePersonalAISocket();
  const [inputValue, setInputValue] = useState('');
  const [greeting, setGreeting] = useState('');
  const chatLogRef = useRef<HTMLDivElement>(null);
  const activityLogRef = useRef<HTMLDivElement>(null);
  const [voiceActive, setVoiceActive] = useState(false);

  const quotes = [
    "The best way to predict the future is to invent it.",
    "Focus is a matter of deciding what things you're not going to do.",
    "Any sufficiently advanced technology is indistinguishable from magic."
  ];

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('Good Morning, Sir.');
    else if (hour < 18) setGreeting('Good Afternoon, Sir.');
    else setGreeting('Good Evening, Sir.');
  }, []);

  useEffect(() => {
    if (chatLogRef.current) {
      chatLogRef.current.scrollTop = chatLogRef.current.scrollHeight;
    }
  }, [messages]);

  useEffect(() => {
    if (activityLogRef.current) {
      activityLogRef.current.scrollTop = activityLogRef.current.scrollHeight;
    }
  }, [activityLogs]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputValue.trim()) return;
    sendToBrain(inputValue);
    setInputValue('');
  };

  return (
    <div className="bg-slate-900 text-slate-50 h-screen font-sans p-8 grid grid-cols-1 md:grid-cols-[1fr_350px] gap-8 box-border overflow-hidden">
      
      {/* Main Column */}
      <div className="flex flex-col gap-8 h-full overflow-hidden">
        
        {/* Header Panel */}
        <div className="bg-slate-800 rounded-xl p-6 shadow-lg border border-white/5 text-center">
          <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            {greeting}
          </h1>
          <p className="text-slate-400 italic mb-4">
            "{quotes[Math.floor(Math.random() * quotes.length)]}"
          </p>
          <div className="flex items-center justify-center gap-4 text-sm text-slate-400 mt-2">
            <div className="flex items-center gap-1">
              <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-red-500'}`} /> WS
            </div>
            <div className="flex items-center gap-1">
              <div className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" /> API
            </div>
            <button 
              onClick={() => {
                setVoiceActive(!voiceActive);
                if (!voiceActive) logActivity('PersonaPlex-7B Dual-Stream Voice Activated');
                else logActivity('Voice Link Terminated');
              }}
              className={`flex items-center gap-2 px-3 py-1 rounded-full border transition-all ${voiceActive ? 'border-emerald-500 bg-emerald-500/20 text-emerald-400' : 'border-slate-600 hover:border-slate-500'}`}
            >
              <div className={`w-2 h-2 rounded-full ${voiceActive ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse' : 'bg-slate-500'}`} /> 
              PersonaPlex Voice
            </button>
          </div>
        </div>

        {/* Voice Duplex Module (Only visible when active) */}
        {voiceActive && (
          <div className="bg-slate-800 rounded-xl shadow-lg border border-emerald-500/30 flex flex-col p-6 animate-in fade-in slide-in-from-top-4">
            <div className="flex justify-between items-center mb-4">
              <h3 className="text-emerald-400 font-bold flex items-center gap-2">
                <span className="relative flex h-3 w-3">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                </span>
                PersonaPlex-7B Full-Duplex Link
              </h3>
              <span className="text-xs neon-text-cyan px-2 py-1 uppercase tracking-widest">
                Voice State
              </span>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-8 flex flex-col items-center justify-center min-h-[120px]">
              <VoiceWaveform />
              <p className="text-slate-400 text-sm mt-6 animate-pulse">Speak freely, SPARK is listening concurrently...</p>
            </div>
          </div>
        )}

        {/* Chat Container */}
        <div className="bg-slate-800 rounded-xl shadow-lg border border-white/5 flex flex-col flex-1 overflow-hidden p-6">
          <div ref={chatLogRef} className="flex-1 overflow-y-auto mb-4 flex flex-col gap-4 pr-4">
            {messages.map((m) => (
              <div
                key={m.id}
                className={`p-4 rounded-lg max-w-[85%] leading-relaxed animate-in slide-in-from-bottom-2 ${
                  m.sender === 'user'
                    ? 'bg-blue-500/10 border border-blue-500/20 self-end rounded-br-none'
                    : 'bg-emerald-500/10 border border-emerald-500/20 self-start rounded-bl-none'
                }`}
                dangerouslySetInnerHTML={{ __html: m.text }}
              />
            ))}
          </div>
          
          <form className="flex gap-2" onSubmit={handleSubmit}>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type a command or ask a question..."
              className="flex-1 bg-black/20 border border-white/10 text-white p-4 rounded-lg focus:outline-none focus:border-blue-500 focus:shadow-[0_0_10px_rgba(59,130,246,0.5)] transition-all"
            />
            <button
              type="submit"
              className="bg-blue-500 hover:brightness-110 text-white font-bold py-4 px-6 rounded-lg transition-all active:scale-95"
            >
              Execute
            </button>
          </form>
        </div>
      </div>

      {/* Side Column */}
      <div className="flex flex-col gap-4 h-full overflow-hidden">
        
        {/* Quick Launch Panel */}
        <div className="bg-slate-800 rounded-xl p-6 shadow-lg border border-white/5">
          <h3 className="text-lg font-bold mb-4">Quick Launch</h3>
          <div className="grid grid-cols-2 gap-2">
            {[
              { name: 'GitHub', url: 'https://github.com' },
              { name: 'Calendar', url: 'https://calendar.google.com' },
              { name: 'Mail', url: 'https://gmail.com' },
              { name: 'YouTube', url: 'https://youtube.com' }
            ].map(app => (
              <button
                key={app.name}
                onClick={() => window.open(app.url)}
                className="bg-white/5 border border-white/10 p-3 hover:bg-white/10 transition-colors flex items-center justify-center gap-2 rounded text-sm"
              >
                {app.name}
              </button>
            ))}
          </div>
        </div>

        {/* Active Tasks Panel */}
        <div className="bg-slate-800 rounded-xl p-6 shadow-lg border border-white/5">
          <h3 className="text-lg font-bold mb-4">Active Tasks</h3>
          <ul className="flex flex-col">
            {['Build Brain Layer', 'Connect Duplex Voice', 'Agentic Execution', 'PentAGI Red Team', 'Vane Local Deep Research', 'WiFi-DensePose Routing'].map((task, i) => (
              <li key={i} className="flex items-center gap-2 py-2 border-b border-white/5 last:border-0 text-slate-300">
                <input type="checkbox" defaultChecked={i < 3} className="w-4 h-4 rounded border-slate-600 outline-none accent-blue-500" />
                <span className={i < 3 ? "line-through text-slate-500" : ""}>{task}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Activity Log Panel */}
        <div className="bg-slate-800 rounded-xl p-6 shadow-lg border border-white/5 flex flex-col flex-1 overflow-hidden">
          <h3 className="text-lg font-bold mb-4">Activity Log</h3>
          <div ref={activityLogRef} className="font-mono text-xs text-slate-400 flex-1 overflow-y-auto pr-2 flex flex-col gap-1">
            {activityLogs.map((log, i) => (
              <div key={i}>{log}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
