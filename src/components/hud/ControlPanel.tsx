import { useState, useRef, useEffect } from 'react';
import { CommandEntry } from '@/hooks/useVoiceEngine';
import { Send, Lightbulb, Calendar, Bell, Smartphone, Tv, Lamp, Thermometer } from 'lucide-react';

interface Props {
  commandHistory: CommandEntry[];
  aiResponse: string;
  transcript: string;
  onProcessInput: (text: string) => void;
  status: string;
}

const SUGGESTIONS = [
  'System Status', 'Weather Report', 'Security Scan',
  'Run Diagnostics', 'Current Time', 'Help'
];

const MOCK_CALENDAR = [
  { time: '14:30', title: 'Neural sync calibration', priority: 'high' },
  { time: '16:00', title: 'Mission briefing — Sector 7', priority: 'medium' },
  { time: '18:45', title: 'System maintenance window', priority: 'low' },
];

const MOCK_REMINDERS = [
  { text: 'Update firewall signatures', priority: 'high', done: false },
  { text: 'Review anomaly report #2847', priority: 'medium', done: false },
  { text: 'Backup neural weights', priority: 'low', done: true },
  { text: 'Deploy patch 4.1.7', priority: 'high', done: false },
];

const DEVICES = [
  { icon: <Smartphone size={14} />, name: 'Mobile', active: true },
  { icon: <Tv size={14} />, name: 'Display', active: true },
  { icon: <Lamp size={14} />, name: 'Lighting', active: false },
  { icon: <Thermometer size={14} />, name: 'Climate', active: true },
];

const TASK_LOG = [
  { color: '#00ff88', text: '[OK] Neural net initialized', time: '00:00:01' },
  { color: '#00f5ff', text: '[INFO] Loading knowledge base...', time: '00:00:03' },
  { color: '#00f5ff', text: '[INFO] Quantum DB connected', time: '00:00:05' },
  { color: '#ffb800', text: '[WARN] Firewall learning mode', time: '00:00:08' },
  { color: '#00ff88', text: '[OK] All systems operational', time: '00:00:12' },
];

export default function ControlPanel({ commandHistory, aiResponse, transcript, onProcessInput, status }: Props) {
  const [inputText, setInputText] = useState('');
  const [deviceStates, setDeviceStates] = useState(DEVICES.map(d => d.active));
  const logRef = useRef<HTMLDivElement>(null);
  const [taskLog, setTaskLog] = useState(TASK_LOG);

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [commandHistory]);

  const handleSend = () => {
    if (!inputText.trim()) return;
    onProcessInput(inputText);
    setInputText('');
  };

  const toggleDevice = (i: number) => {
    setDeviceStates(prev => {
      const next = [...prev];
      next[i] = !next[i];
      return next;
    });
    setTaskLog(prev => [...prev, {
      color: deviceStates[i] ? '#ff3b3b' : '#00ff88',
      text: `[${deviceStates[i] ? 'OFF' : 'ON'}] ${DEVICES[i].name} toggled`,
      time: new Date().toTimeString().slice(0, 8),
    }]);
  };

  const priorityColors: Record<string, string> = {
    high: '#ff3b3b', medium: '#ffb800', low: '#00f5ff'
  };

  return (
    <div className="flex flex-col h-full gap-2 overflow-y-auto scrollbar-hud p-2 animate-boot-right" style={{ animationDelay: '0.3s' }}>
      {/* Panel header */}
      <div className="flex items-center justify-between pb-1 border-b border-hud-cyan/20">
        <span className="font-orbitron text-[9px] tracking-widest neon-text">SPARK CONTROL</span>
        <div className="flex gap-1 items-center">
          <div className={`w-1.5 h-1.5 rounded-full ${status === 'idle' ? 'bg-hud-cyan/60' :
              status === 'listening' ? 'bg-hud-green animate-pulse' :
                status === 'thinking' ? 'bg-hud-amber animate-pulse' : 'bg-hud-blue animate-pulse'
            }`} />
          <span className="font-mono-tech text-[8px] text-hud-cyan/60">{status.toUpperCase()}</span>
        </div>
      </div>

      {/* Command History */}
      <div>
        <div className="font-orbitron text-[8px] tracking-widest text-hud-cyan/60 mb-1">◈ COMMAND LOG</div>
        <div ref={logRef} className="h-24 overflow-y-auto scrollbar-hud flex flex-col gap-1 p-1.5 rounded border border-hud-cyan/15 bg-black/30">
          {commandHistory.slice(-8).map(entry => (
            <div key={entry.id} className="flex gap-1.5">
              <span className="font-mono-tech text-[8px] text-hud-cyan/30 shrink-0">
                {entry.timestamp.toLocaleTimeString('en', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </span>
              <span className={`font-mono-tech text-[8px] ${entry.type === 'user' ? 'text-hud-amber' : 'text-hud-cyan/80'}`}>
                {entry.type === 'user' ? '▶ ' : '◀ '}{entry.text}
              </span>
            </div>
          ))}
          {transcript && (
            <div className="font-mono-tech text-[8px] text-hud-green animate-pulse">
              ◉ {transcript}...
            </div>
          )}
        </div>
      </div>

      {/* AI Response */}
      {(aiResponse || status === 'responding') && (
        <div className="p-2 rounded border border-hud-blue/30 bg-hud-blue/5">
          <div className="font-orbitron text-[8px] text-hud-blue/60 mb-1">◈ SPARK RESPONSE</div>
          <p className="font-rajdhani text-xs text-hud-cyan/90 leading-relaxed">
            {aiResponse}
            {status === 'responding' && <span className="animate-type-cursor">█</span>}
          </p>
        </div>
      )}

      {/* Text input */}
      <div className="flex gap-1.5">
        <input
          value={inputText}
          onChange={e => setInputText(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          placeholder="ENTER COMMAND..."
          className="flex-1 bg-black/40 border border-hud-cyan/25 rounded px-2 py-1.5 font-mono-tech text-[10px] text-hud-cyan placeholder-hud-cyan/30 outline-none focus:border-hud-cyan/60 transition-colors"
          style={{ caretColor: 'hsl(186 100% 50%)' }}
        />
        <button
          onClick={handleSend}
          className="hud-btn px-2"
        >
          <Send size={12} />
        </button>
      </div>

      {/* Suggestions */}
      <div>
        <div className="font-orbitron text-[8px] tracking-widest text-hud-cyan/60 mb-1">◈ SUGGESTIONS</div>
        <div className="flex flex-wrap gap-1">
          {SUGGESTIONS.map(s => (
            <button
              key={s}
              onClick={() => onProcessInput(s)}
              className="font-orbitron text-[8px] px-2 py-0.5 rounded border border-hud-cyan/25 text-hud-cyan/70 hover:border-hud-cyan/60 hover:text-hud-cyan hover:bg-hud-cyan/10 transition-all duration-150"
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Task log */}
      <div>
        <div className="font-orbitron text-[8px] tracking-widest text-hud-cyan/60 mb-1">◈ EXECUTION LOG</div>
        <div className="h-20 overflow-y-auto scrollbar-hud bg-black/40 rounded border border-hud-cyan/15 p-1.5">
          {taskLog.map((entry, i) => (
            <div key={i} className="flex gap-2 font-mono-tech text-[8px] leading-4">
              <span className="text-hud-cyan/30 shrink-0">{entry.time}</span>
              <span style={{ color: entry.color }}>{entry.text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Connected devices */}
      <div>
        <div className="font-orbitron text-[8px] tracking-widest text-hud-cyan/60 mb-1">◈ IOT DEVICES</div>
        <div className="grid grid-cols-2 gap-1">
          {DEVICES.map((d, i) => (
            <button
              key={d.name}
              onClick={() => toggleDevice(i)}
              className={`flex items-center gap-1.5 p-1.5 rounded border transition-all duration-200 ${deviceStates[i]
                  ? 'border-hud-cyan/40 bg-hud-cyan/8 text-hud-cyan'
                  : 'border-hud-cyan/15 bg-transparent text-hud-cyan/30'
                }`}
            >
              {d.icon}
              <span className="font-orbitron text-[8px]">{d.name}</span>
              <div className={`ml-auto w-1.5 h-1.5 rounded-full ${deviceStates[i] ? 'bg-hud-green animate-pulse' : 'bg-hud-cyan/20'}`} />
            </button>
          ))}
        </div>
      </div>

      {/* Calendar */}
      <div>
        <div className="font-orbitron text-[8px] tracking-widest text-hud-cyan/60 mb-1 flex items-center gap-1">
          <Calendar size={9} /> UPCOMING
        </div>
        <div className="flex flex-col gap-1">
          {MOCK_CALENDAR.map((ev, i) => (
            <div key={i} className="flex items-center gap-2 p-1.5 rounded border border-hud-cyan/10">
              <span className="font-mono-tech text-[8px] text-hud-cyan/50 shrink-0">{ev.time}</span>
              <span className="font-rajdhani text-[10px] text-hud-cyan/80 flex-1 truncate">{ev.title}</span>
              <div className="w-1.5 h-1.5 rounded-full shrink-0"
                style={{ background: priorityColors[ev.priority] }} />
            </div>
          ))}
        </div>
      </div>

      {/* Reminders */}
      <div>
        <div className="font-orbitron text-[8px] tracking-widest text-hud-cyan/60 mb-1 flex items-center gap-1">
          <Bell size={9} /> REMINDERS
        </div>
        <div className="flex flex-col gap-1">
          {MOCK_REMINDERS.map((r, i) => (
            <div key={i} className={`flex items-center gap-2 px-1.5 py-1 rounded border border-hud-cyan/10 ${r.done ? 'opacity-40' : ''}`}>
              <div className="w-1.5 h-1.5 rounded-full shrink-0"
                style={{ background: r.done ? '#555' : priorityColors[r.priority] }} />
              <span className={`font-rajdhani text-[10px] flex-1 ${r.done ? 'line-through text-hud-cyan/30' : 'text-hud-cyan/80'}`}>
                {r.text}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
