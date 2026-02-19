import { useState, useEffect } from 'react';
import { Bot, Play, Pause, CheckCircle, Clock, AlertCircle } from 'lucide-react';

type TaskStatus = 'pending' | 'running' | 'done' | 'error';
interface AgentTask { id: string; name: string; status: TaskStatus; progress: number; log: string; }

const INITIAL_TASKS: AgentTask[] = [
  { id: '1', name: 'Analyze threat vectors', status: 'done', progress: 100, log: 'Completed — 0 threats found' },
  { id: '2', name: 'Update knowledge base', status: 'running', progress: 67, log: 'Fetching sector 7 data...' },
  { id: '3', name: 'Optimize neural weights', status: 'pending', progress: 0, log: 'Queued' },
  { id: '4', name: 'Sync IoT device mesh', status: 'pending', progress: 0, log: 'Queued' },
  { id: '5', name: 'Generate summary report', status: 'pending', progress: 0, log: 'Awaiting dependencies' },
];

const LOG_LINES = [
  { color: '#00ff88', text: '> Agent initialized. Neural pathways loaded.' },
  { color: '#00f5ff', text: '> Scanning knowledge graph nodes...' },
  { color: '#00f5ff', text: '> Loading task queue: 5 items' },
  { color: '#ffb800', text: '> Warning: Sector 7 data partially stale' },
  { color: '#00f5ff', text: '> Initiating adaptive learning loop...' },
  { color: '#00ff88', text: '> Task #1 completed in 234ms' },
  { color: '#0066ff', text: '> Task #2 running [67%]' },
];

const statusIcon = {
  pending: <Clock size={11} className="text-hud-cyan/40" />,
  running: <div className="w-2.5 h-2.5 border border-hud-amber rounded-full animate-spin border-t-transparent" />,
  done: <CheckCircle size={11} className="text-hud-green" />,
  error: <AlertCircle size={11} className="text-hud-red" />,
};

const statusColor: Record<TaskStatus, string> = {
  pending: '#00f5ff40', running: '#ffb800', done: '#00ff88', error: '#ff3b3b'
};

export default function AgentModule() {
  const [tasks, setTasks] = useState(INITIAL_TASKS);
  const [running, setRunning] = useState(true);
  const [logs, setLogs] = useState(LOG_LINES);

  useEffect(() => {
    if (!running) return;
    const interval = setInterval(() => {
      setTasks(prev => prev.map(t => {
        if (t.status === 'running') {
          const next = Math.min(100, t.progress + Math.random() * 3);
          if (next >= 100) {
            setLogs(l => [...l.slice(-20), { color: '#00ff88', text: `> Task "${t.name}" completed ✓` }]);
            return { ...t, progress: 100, status: 'done', log: 'Completed successfully' };
          }
          return { ...t, progress: next, log: `Processing... ${Math.round(next)}%` };
        }
        if (t.status === 'pending' && prev.every(x => x.id < t.id ? x.status === 'done' : true)) {
          setLogs(l => [...l.slice(-20), { color: '#ffb800', text: `> Starting task: "${t.name}"` }]);
          return { ...t, status: 'running', log: 'Starting...' };
        }
        return t;
      }));
    }, 300);
    return () => clearInterval(interval);
  }, [running]);

  const reset = () => {
    setTasks(INITIAL_TASKS);
    setLogs(LOG_LINES);
    setRunning(true);
  };

  return (
    <div className="flex flex-col gap-4 p-4 h-full overflow-y-auto scrollbar-hud">
      <div className="flex items-center justify-between pb-2 border-b border-hud-cyan/20">
        <div className="flex items-center gap-2">
          <Bot size={14} className="text-hud-cyan" />
          <span className="font-orbitron text-xs tracking-widest neon-text">AUTONOMOUS AGENT</span>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setRunning(v => !v)}
            className="hud-btn flex-row gap-1 px-2 py-1">
            {running ? <Pause size={11} /> : <Play size={11} />}
            <span className="font-orbitron text-[8px]">{running ? 'PAUSE' : 'RESUME'}</span>
          </button>
          <button onClick={reset}
            className="font-orbitron text-[8px] px-2 py-1 rounded border border-hud-cyan/25 text-hud-cyan/60 hover:text-hud-cyan">
            RESET
          </button>
        </div>
      </div>

      {/* Task queue */}
      <div className="flex flex-col gap-2">
        <div className="font-orbitron text-[9px] text-hud-cyan/60">◈ TASK QUEUE</div>
        {tasks.map((task, i) => (
          <div key={task.id} className="hud-panel rounded p-2">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono-tech text-[8px] text-hud-cyan/30">#{i + 1}</span>
              {statusIcon[task.status]}
              <span className="font-rajdhani text-xs text-hud-cyan/80 flex-1">{task.name}</span>
              <span className="font-mono-tech text-[8px]" style={{ color: statusColor[task.status] }}>
                {task.status.toUpperCase()}
              </span>
            </div>
            {task.status === 'running' && (
              <div className="h-0.5 rounded-full bg-black/40 overflow-hidden">
                <div className="h-full rounded-full transition-all duration-300"
                  style={{ width: `${task.progress}%`, background: '#ffb800', boxShadow: '0 0 4px #ffb800' }} />
              </div>
            )}
            <div className="font-mono-tech text-[8px] text-hud-cyan/40 mt-0.5">{task.log}</div>
          </div>
        ))}
      </div>

      {/* Agent log */}
      <div>
        <div className="font-orbitron text-[9px] text-hud-cyan/60 mb-2">◈ AGENT LOG</div>
        <div className="h-40 overflow-y-auto scrollbar-hud bg-black/50 rounded border border-hud-cyan/15 p-2">
          {logs.map((l, i) => (
            <div key={i} className="font-mono-tech text-[9px] leading-4" style={{ color: l.color }}>{l.text}</div>
          ))}
          <div className="font-mono-tech text-[9px] text-hud-cyan/50 animate-type-cursor">█</div>
        </div>
      </div>
    </div>
  );
}
